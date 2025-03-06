from django.urls import path
from .views import RegisterView, LoginView, UserProfileView, signup_page, login_page, send_otp, verify_otp, VerifyEmailView
from django.shortcuts import render

urlpatterns = [
    # API Endpoints
    path("signup/", RegisterView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("dashboard/", lambda request: render(request, "authentication/dashboard.html"), name="dashboard"),
    path("profile/", UserProfileView.as_view(), name="user-profile"),
    path("send-otp/", send_otp, name="send-otp"),
    path("verify-otp/", verify_otp, name="verify-otp"),

    # HTML Pages
    path("signup-page/", signup_page, name="signup-page"),
    path("login-page/", login_page, name="login-page"),
]