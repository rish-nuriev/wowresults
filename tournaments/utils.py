from django.http import HttpResponse
from tournaments import redis_tools
from tournaments.tasks import async_error_logging

REDIS_CONNECTION = redis_tools.get_redis_connection()


def check_api_requests(max_count=0):
    error_message = 'We have reached the limit of the API requests'
    api_requests_count = redis_tools.get_api_requests_count(REDIS_CONNECTION)
    if max_count and api_requests_count >= max_count:
        async_error_logging.delay(error_message)
        return HttpResponse(error_message)
