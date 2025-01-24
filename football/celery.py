import os
from celery import Celery # type: ignore

# задать стандартный модуль настроек Django
# для программы 'celery'.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "football.settings")
app = Celery("football")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
