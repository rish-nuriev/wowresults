import os
from celery import Celery
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env так же, как в manage.py
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Устанавливаем настройки Django (по умолчанию local)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "football.settings.local")

app = Celery("football")

# Подгружаем настройки Django с префиксом CELERY_
# Например, CELERY_BROKER_URL, CELERY_RESULT_BACKEND
app.config_from_object("django.conf:settings", namespace="CELERY")

# Автоматически искать tasks.py во всех приложениях
app.autodiscover_tasks()
