from datetime import timezone, datetime

from django.conf import settings

import redis


def get_redis_connection():
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASS,
    )

def get_api_requests_count(r):
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    key = f"{today_str}_api_requests_count"
    if not r.exists(key):
        r.set(key, 0)
        r.expire(key, 86400)

    return int(r.get(key))

def increase_api_requests_count(r, cnt=1):
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    key = f"{today_str}_api_requests_count"
    r.incr(key, cnt)
