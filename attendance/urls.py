from django.urls import path

from .views import (
    capture_page,
    course_students,
    dashboard,
    reports,
    upload_face_frame,
    upload_training_sample,
)


urlpatterns = [
    path("dashboard/", dashboard, name="dashboard"),
    path("course/<int:course_id>/students/", course_students, name="course_students"),
    path("capture/", capture_page, name="capture"),
    path("capture/upload/", upload_face_frame, name="upload_face_frame"),
    path("students/<int:student_id>/training-sample/", upload_training_sample, name="upload_training_sample"),
    path("reports/", reports, name="reports"),
]

