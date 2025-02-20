from django_email_verification import send_email
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse
from .forms import UserRegistrationForm


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

            # Сделать пользователя неверифицированным
            # пока не пройдет проверку по Email
            user.is_active = False
            send_email(user)

            return HttpResponseRedirect(reverse("login"))

    else:
        user_form = UserRegistrationForm()
    return render(request, "account/register.html", {"user_form": user_form})


@login_required
def dashboard(request):
    return render(request, "account/dashboard.html", {"section": "dashboard"})
