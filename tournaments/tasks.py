import logging
from celery import shared_task
from tournaments.models import Team

logger = logging.getLogger("basic_logger")


@shared_task
def async_error_logging(message):
    logger.error(message)


@shared_task
def async_save_raw_teams(teams):
    Team.save_raw_teams(teams)


@shared_task
def async_save_multiple_logos(teams):
    Team.save_multiple_logos(teams)
