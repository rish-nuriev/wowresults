import logging
from celery import shared_task

logger = logging.getLogger("basic_logger")

@shared_task
def async_error_logging(message):
    logger.error(message)
