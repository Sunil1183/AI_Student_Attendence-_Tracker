from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.models import StudentProfile, FacultyProfile


class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    program = models.CharField(max_length=100, blank=True)
    session = models.CharField(max_length=50, blank=True)
    section = models.CharField(max_length=20, blank=True)
    faculty = models.ForeignKey(
        FacultyProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
    )

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class ClassSession(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sessions")
    date = models.DateField(default=timezone.now)
    start_time = models.TimeField(default=timezone.now)
    end_time = models.TimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_sessions",
    )

    def __str__(self) -> str:
        return f"{self.course.code} - {self.date}"


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        LATE = "LATE", "Late"
        LEAVE = "LEAVE", "Leave"

    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name="records")
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="attendance_records")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)
    marked_at = models.DateTimeField(auto_now_add=True)
    via_face_recognition = models.BooleanField(default=False)

    class Meta:
        unique_together = ("session", "student")

    def __str__(self) -> str:
        return f"{self.session} - {self.student} - {self.status}"


class FaceSample(models.Model):
    """Stores raw face images used to train the recognizer."""

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="face_samples")
    image = models.ImageField(upload_to="students/face_samples/")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Face sample for {self.student}"

