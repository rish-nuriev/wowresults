from datetime import timedelta, timezone, datetime

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

def get_date_to_check(r, date):
    while r.exists(f"{date}_processed"):
        date += timedelta(days=1)
    return date


def set_date_processed(r, date):
    # значение ключа пустая строка т.к. нас интересует лишь наличие ключа
    r.set(f"{date}_processed", "")
