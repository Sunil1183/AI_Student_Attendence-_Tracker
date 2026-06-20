from __future__ import annotations

import base64
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.models import StudentProfile, User
from .face_engine import recognize_students_from_image_bytes
from .models import AttendanceRecord, ClassSession, Course, FaceSample


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    today = date.today()
    total_students = StudentProfile.objects.count()

    today_sessions = ClassSession.objects.filter(date=today)
    today_attendance = AttendanceRecord.objects.filter(session__in=today_sessions)

    present_today = today_attendance.filter(status=AttendanceRecord.Status.PRESENT).count()
    absent_today = today_attendance.filter(status=AttendanceRecord.Status.ABSENT).count()

    course_count = Course.objects.count()
    month_session_count = ClassSession.objects.filter(date__month=today.month).count()

    user: User = request.user  # type: ignore[assignment]
    student_profile = StudentProfile.objects.filter(user=user).first()

    my_total = my_present = None
    my_attendance_percent = None
    my_recent_records = []
    recent_records = []

    if student_profile:
        my_qs = (
            student_profile.attendance_records.select_related("session", "session__course")
            .order_by("-session__date", "-marked_at")
        )
        my_total = my_qs.count()
        my_present = my_qs.filter(status=AttendanceRecord.Status.PRESENT).count()
        if my_total:
            my_attendance_percent = round(my_present * 100.0 / my_total, 1)
        my_recent_records = list(my_qs[:5])
    else:
        recent_records = list(
            AttendanceRecord.objects.select_related("student", "session", "session__course")
            .order_by("-marked_at")[:5]
        )

    monthly_stats = (
        AttendanceRecord.objects.filter(marked_at__date__month=today.month)
        .values("session__date")
        .annotate(total=Count("id"))
        .order_by("session__date")
    )

    context = {
        "total_students": total_students,
        "present_today": present_today,
        "absent_today": absent_today,
        "course_count": course_count,
        "month_session_count": month_session_count,
        "student_profile": student_profile,
        "my_total": my_total,
        "my_present": my_present,
        "my_attendance_percent": my_attendance_percent,
        "my_recent_records": my_recent_records,
        "recent_records": recent_records,
        "monthly_stats": monthly_stats,
        "today_sessions": today_sessions.select_related("course"),
        "today": today,
    }
    return render(request, "attendance/dashboard.html", context)


@login_required
def course_students(request: HttpRequest, course_id: int) -> HttpResponse:
    course = get_object_or_404(Course, id=course_id)
    today = date.today()
    session, _ = ClassSession.objects.get_or_create(
        course=course,
        date=today,
        defaults={"created_by": request.user},
    )

    students = StudentProfile.objects.all().order_by("roll_number")

    if request.method == "POST":
        updated = 0
        for student in students:
            key = f"status_{student.id}"
            status_value = request.POST.get(key)
            if not status_value:
                continue
            record, _ = AttendanceRecord.objects.get_or_create(
                session=session,
                student=student,
                defaults={"status": status_value},
            )
            if record.status != status_value:
                record.status = status_value
                record.save(update_fields=["status"])
            updated += 1

        messages.success(request, f"Updated attendance for {updated} students.")
        return redirect("attendance:course_students", course_id=course.id)

    existing_records = {
        rec.student_id: rec
        for rec in AttendanceRecord.objects.filter(session=session).select_related("student")
    }

    return render(
        request,
        "attendance/course_students.html",
        {
            "course": course,
            "students": students,
            "session": session,
            "existing_records": existing_records,
        },
    )


@login_required
@require_GET
def capture_page(request: HttpRequest) -> HttpResponse:
    courses = Course.objects.all().order_by("name")
    return render(request, "attendance/capture.html", {"courses": courses})


@login_required
@require_POST
def upload_face_frame(request: HttpRequest) -> JsonResponse:
    """
    Receives one or more base64-encoded frames from the browser and marks
    attendance for all recognized students in the **last** frame.  When the
    client sends a sequence of frames we run a simple liveness check to make
    sure the camera feed wasn't just pointed at a static photograph.
    """

    user: User = request.user  # type: ignore[assignment]
    course_id = request.POST.get("course_id")
    # new field: the front end may send a JSON list of frames
    frames_data = request.POST.get("frames")
    frame_data = request.POST.get("frame")  # legacy support

    if not course_id or (not frames_data and not frame_data):
        return JsonResponse({"success": False, "error": "Missing course or frame data."}, status=400)

    course = get_object_or_404(Course, id=course_id)
    today = date.today()
    session, _ = ClassSession.objects.get_or_create(
        course=course,
        date=today,
        defaults={"created_by": user},
    )

    # decode any base64 strings we received
    frames: list[bytes] = []
    if frames_data:
        try:
            import json

            raw_list = json.loads(frames_data)
            for item in raw_list:
                if isinstance(item, str) and "," in item:
                    _, item = item.split(",", 1)
                frames.append(base64.b64decode(item))
        except (ValueError, json.JSONDecodeError) as exc:  # noqa: PERF203
            return JsonResponse({"success": False, "error": f"Invalid frames data: {exc}"}, status=400)
    elif frame_data:
        if "," in frame_data:
            _, frame_data = frame_data.split(",", 1)
        try:
            frames.append(base64.b64decode(frame_data))
        except (TypeError, ValueError) as exc:  # noqa: PERF203
            return JsonResponse({"success": False, "error": f"Invalid image data: {exc}"}, status=400)

    recognized_students = list(
        recognize_students_from_image_bytes(frames=frames)
    )

    # if we got an empty list but supplied multiple frames it may be because
    # liveness check failed; communicate a more helpful message in that case.
    if not recognized_students and len(frames) > 1:
        # do a quick sanity check to see if the sequence was probably static
        # (this duplicates some logic from the engine but keeps the view simple).
        from .face_engine import _is_live_sequence

        if not _is_live_sequence(frames):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Liveness check failed – make sure your webcam is pointed at you and try moving slightly or blinking."
                },
                status=400,
            )

    marked_students: list[dict] = []
    for student in recognized_students:
        record, created = AttendanceRecord.objects.get_or_create(
            session=session,
            student=student,
            defaults={
                "status": AttendanceRecord.Status.PRESENT,
                "via_face_recognition": True,
            },
        )
        if not created and record.status != AttendanceRecord.Status.PRESENT:
            record.status = AttendanceRecord.Status.PRESENT
            record.via_face_recognition = True
            record.marked_at = timezone.now()
            record.save(update_fields=["status", "via_face_recognition", "marked_at"])

        marked_students.append(
            {
                "id": student.id,
                "roll_number": student.roll_number,
                "name": student.user.get_full_name() or student.user.username,
            }
        )

    return JsonResponse({"success": True, "marked_students": marked_students})


@login_required
@require_POST
def upload_training_sample(request: HttpRequest, student_id: int) -> JsonResponse:
    student = get_object_or_404(StudentProfile, id=student_id)
    frame_data = request.POST.get("frame")
    if not frame_data:
        return JsonResponse({"success": False, "error": "Missing frame data."}, status=400)

    if "," in frame_data:
        _, frame_data = frame_data.split(",", 1)

    try:
        image_bytes = base64.b64decode(frame_data)
    except (TypeError, ValueError) as exc:  # noqa: PERF203
        return JsonResponse({"success": False, "error": f"Invalid image data: {exc}"}, status=400)

    from django.core.files.base import ContentFile

    file_name = f"{student.roll_number}_{timezone.now().strftime('%Y%m%d%H%M%S')}.jpg"
    sample = FaceSample(student=student)
    sample.image.save(file_name, ContentFile(image_bytes))
    sample.save()

    return JsonResponse({"success": True})


@login_required
def reports(request: HttpRequest) -> HttpResponse:
    courses = Course.objects.all().order_by("name")
    selected_course_id = request.GET.get("course")
    selected_date = request.GET.get("date")

    records = AttendanceRecord.objects.select_related("student", "session", "session__course")

    if selected_course_id:
        records = records.filter(session__course_id=selected_course_id)
    if selected_date:
        records = records.filter(session__date=selected_date)

    return render(
        request,
        "attendance/reports.html",
        {
            "courses": courses,
            "records": records,
            "selected_course_id": selected_course_id,
            "selected_date": selected_date,
        },
    )

