from django.urls import include, path
from django.contrib.auth.views import (
    LoginView,
    PasswordResetView,
    PasswordResetConfirmView,
    PasswordChangeView,
)
from account import views
from account.forms import (
    PrettyAuthenticationForm,
    PrettyPasswordResetForm,
    PrettySetPasswordForm,
    PrettyPasswordChangeForm,
)

urlpatterns = [
    path(
        "login/", LoginView.as_view(form_class=PrettyAuthenticationForm), name="login"
    ),
    path(
        "password_reset/",
        PasswordResetView.as_view(form_class=PrettyPasswordResetForm),
        name="password_reset",
    ),
    path(
        "password_change/",
        PasswordChangeView.as_view(form_class=PrettyPasswordChangeForm),
        name="password_change",
    ),
    path(
        "reset/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(form_class=PrettySetPasswordForm),
        name="password_reset_confirm",
    ),
    path("", include("django.contrib.auth.urls")),
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("edit/", views.edit, name="edit"),
]
