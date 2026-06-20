from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        FACULTY = "FACULTY", "Faculty"
        STUDENT = "STUDENT", "Student"

    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.STUDENT,
        help_text="Determines what the user can access in the system.",
    )

    def is_admin(self) -> bool:
        return self.role == self.Roles.ADMIN or self.is_superuser

    def is_faculty(self) -> bool:
        return self.role == self.Roles.FACULTY

    def is_student(self) -> bool:
        return self.role == self.Roles.STUDENT


class FacultyProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="faculty_profile",
    )
    full_name = models.CharField(max_length=150)
    department = models.CharField(max_length=100, blank=True)
    designation = models.CharField(max_length=100, blank=True)

    def __str__(self) -> str:
        return self.full_name


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    roll_number = models.CharField(max_length=30, unique=True)
    program = models.CharField(max_length=100, blank=True)
    batch = models.CharField(max_length=50, blank=True)
    section = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(
        upload_to="students/photos/",
        blank=True,
        null=True,
    )

    def __str__(self) -> str:
        return f"{self.roll_number} - {self.user.get_full_name() or self.user.username}"

