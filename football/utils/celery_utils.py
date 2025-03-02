import logging
from celery.app.control import Control

logger = logging.getLogger("basic_logger")


def check_celery_connection():
    control = Control()
    try:
        ping_response = control.ping()
        return bool(ping_response)
    except Exception as e:
        logger.error(e)
        return False
