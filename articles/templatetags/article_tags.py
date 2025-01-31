from django import template
from django.db.models import Count
from django.utils.http import urlencode
from articles.models import Article

register = template.Library()


@register.inclusion_tag("articles/similar.html")
def show_similar_articles(article):
    # Список схожих постов
    articles_tags_ids = article.tags.values_list("id", flat=True)
    similar_articles = Article.published.filter(tags__in=articles_tags_ids).exclude(
        id=article.id
    )
    similar_articles = similar_articles.annotate(same_tags=Count("tags")).order_by(
        "-same_tags", "-time_create"
    )[:4]
    return {"similar_articles": similar_articles}


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    query = context["request"].GET.dict()
    query.update(kwargs)
    return urlencode(query)
