from django.urls import path

from .views import StudentLoginView, StudentSignUpView, logout_view, student_profile


urlpatterns = [
    path("login/", StudentLoginView.as_view(), name="login"),
    path("signup/", StudentSignUpView.as_view(), name="signup"),
    path("logout/", logout_view, name="logout"),
    path("me/", student_profile, name="profile"),
]

