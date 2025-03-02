import logging
from celery.app.control import Inspect
from football.celery import app


logger = logging.getLogger("basic_logger")


def check_celery_connection():
    """
    Функция проверяет запущен ли celery.
    Нужна для того чтобы выполнить задачу (например отправить письмо)
    обычным способом в случае если celery недоступен.
    """
    try:
        inspector = Inspect(app=app)
        active_tasks = inspector.active()
        if active_tasks:
            # есть активные воркеры celery
            return True
        else:
            # активных воркеров celery нет
            return False
    except Exception as e:
        # логируем неизвестную ошибку
        logger.error(e)
        return False
