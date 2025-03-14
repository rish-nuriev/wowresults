from celery import shared_task
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm


@shared_task
def send_password_reset_mail(
    subject_template_name,
    email_template_name,
    context,
    from_email,
    to_email,
    html_email_template_name,
):
    context["user"] = User.objects.get(pk=context["user"])

    PasswordResetForm.send_mail(
        None,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name,
    )
