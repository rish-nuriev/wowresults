from django_email_verification import send_email
from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse
from .forms import UserRegistrationForm, UserEditForm, ProfileEditForm
from .models import Profile


def register(request):
    if request.method == "POST":
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            user_form.save(commit=False)
            user_email = user_form.cleaned_data["email"]
            user_username = user_form.cleaned_data["username"]
            user_password = user_form.cleaned_data["password"]

            # Создать пользователя
            user = User.objects.create_user(
                username=user_username, email=user_email, password=user_password
            )
            Profile.objects.create(user=user)

            # Сделать пользователя неверифицированным
            # пока не пройдет проверку по Email
            user.is_active = False
            send_email(user)
            messages.success(
                request,
                f"Письмо с инструкцией по активации \
                                        отправлено на {user_email}",
            )

            return HttpResponseRedirect(reverse("login"))

    else:
        user_form = UserRegistrationForm()
    return render(request, "account/register.html", {"user_form": user_form})


@login_required
def dashboard(request):
    return render(request, "account/dashboard.html", {"section": "dashboard"})


@login_required
def edit(request):
    if request.method == "POST":
        user_form = UserEditForm(instance=request.user, data=request.POST)
        profile_form = ProfileEditForm(
            instance=request.user.profile, data=request.POST, files=request.FILES
        )
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Профиль успешно обновлен')
        else:
            messages.error(request, 'Ошибка редактирования профиля')
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=request.user.profile)
    return render(
        request,
        "account/edit.html",
        {"user_form": user_form, "profile_form": profile_form,
         "noimage": settings.DEFAULT_PROFILE_IMAGE},
    )
