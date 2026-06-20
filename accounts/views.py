from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import StudentSignUpForm, LoginForm
from .models import StudentProfile, User


class StudentLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm


class StudentSignUpView(CreateView):
    model = User
    form_class = StudentSignUpForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("attendance:dashboard")

    def form_valid(self, form: StudentSignUpForm) -> HttpResponse:
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Welcome! Your student account has been created.")
        return response


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("landing")


@login_required
def student_profile(request: HttpRequest) -> HttpResponse:
    assert isinstance(request.user, User)
    profile = StudentProfile.objects.filter(user=request.user).first()
    return render(
        request,
        "accounts/student_profile.html",
        {
            "profile": profile,
        },
    )

