import random
from datetime import datetime
from django import template
from django.db.models import Count

from articles.models import Article
from tournaments.models import Tournament

register = template.Library()


@register.inclusion_tag("tournaments/list_tournaments.html")
def show_tournaments(selected=0):
    year = datetime.today().year - 2
    tournaments = Tournament.objects.annotate(total=Count("posts")).filter(
        total__gt=0, season_api_football__gt=year
    )
    return {"tournaments": tournaments, "selected": selected}


@register.inclusion_tag("tournaments/tags.html")
def show_tags_from_taggit():

    allposts = Article.objects.all()
    all_tags = {tag.name:tag.slug for post in allposts for tag in post.tags.all()}
    all_tags_list = list(all_tags)

    random.shuffle(all_tags_list)
    ten_tags = all_tags_list[:10]
    return {"ten_tags": ten_tags, "all_tags": all_tags}
