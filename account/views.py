from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .forms import UserRegistrationForm

def register(request):
    if request.method == "POST":
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            # Создать новый объект пользователя,
            # но пока не сохранять его
            new_user = user_form.save(commit=False)
            # Установить выбранный пароль
            new_user.set_password(user_form.cleaned_data["password"])
            # Сохранить объект User
            new_user.save()
            return render(request, "account/register_done.html", {"new_user": new_user})
    else:
        user_form = UserRegistrationForm()
    return render(request, "account/register.html", {"user_form": user_form})


@login_required
def dashboard(request):
    return render(request, "account/dashboard.html", {"section": "dashboard"})
