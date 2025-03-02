import logging
from celery.exceptions import CeleryError
from football.celery import app

logger = logging.getLogger("basic_logger")


def check_celery_connection():
    """
    Функция проверяет запущен ли celery.
    Нужна для того чтобы выполнить задачу (например отправить письмо) 
    обычным способом в случае если celery недоступен.
    """
    try:
        control = app.control
        ping_response = control.ping(timeout=1)
        if not ping_response:
            raise CeleryError("No response from Celery workers")
        return True
    except CeleryError as e:
        logger.error(e)
        return False
