from django.contrib import admin

from .models import Course, ClassSession, AttendanceRecord, FaceSample


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "program", "session", "section", "faculty")
    search_fields = ("code", "name")
    list_filter = ("program", "session", "section")


@admin.register(ClassSession)
class ClassSessionAdmin(admin.ModelAdmin):
    list_display = ("course", "date", "start_time", "end_time", "created_by")
    list_filter = ("course", "date")


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("session", "student", "status", "marked_at", "via_face_recognition")
    list_filter = ("status", "session__course", "session__date")
    search_fields = ("student__roll_number", "student__user__username")


@admin.register(FaceSample)
class FaceSampleAdmin(admin.ModelAdmin):
    list_display = ("student", "created_at")
    list_filter = ("created_at",)

