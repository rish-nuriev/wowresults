from django.urls import include, path
from django.contrib.auth.views import LoginView, PasswordResetView
from account import views
from account.forms import PrettyAuthenticationForm, PrettyPasswordResetForm

urlpatterns = [
    path(
        "login/", LoginView.as_view(form_class=PrettyAuthenticationForm), name="login"
    ),
    path(
        "password_reset/",
        PasswordResetView.as_view(form_class=PrettyPasswordResetForm),
        name="password_reset",
    ),
    path("", include("django.contrib.auth.urls")),
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
]
