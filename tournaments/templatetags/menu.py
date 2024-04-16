from django import template
from django.db.models import Sum, Count, IntegerField
from django.db.models.functions import Cast
from django.contrib.postgres.aggregates.general import StringAgg

from tournaments.models import Match, Tournament


register = template.Library()


@register.inclusion_tag("tournaments/menu.html")
def show_menu():
    tournaments = Tournament.objects.filter(is_regular=True)
    t_urls = {}
    for t in tournaments[::-1]:
        t_urls[t.title] = t.get_absolute_url()
    return {"tournaments": tournaments, "t_urls": t_urls}
