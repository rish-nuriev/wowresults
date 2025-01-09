from datetime import datetime, timezone
from django import template
from django.db.models import Count

from articles.models import TranslitTag
from tournaments.models import Tournament, Match

register = template.Library()


@register.inclusion_tag("tournaments/list_tournaments.html")
def show_tournaments(selected=0):
    year = datetime.today().year - 2
    tournaments = (
        Tournament.objects.annotate(total=Count("posts"))
        .filter(total__gt=0, season_api_football__gt=year)
        .order_by("-total")
    )
    return {"tournaments": tournaments, "selected": selected}


@register.inclusion_tag("tournaments/tags.html")
def show_tags_from_taggit():
    ten_tags = TranslitTag.get_random_tags(10)
    return {"ten_tags": ten_tags}


@register.inclusion_tag("tournaments/todays_matches.html")
def show_todays_matches():
    today = datetime.now(timezone.utc).date()
    matches = Match.main_matches.get_matches_by_date(today)
    statuses = Match.get_statuses_as_dict()
    return {"matches": matches, "statuses": statuses, "matches_cnt": len(matches)}
