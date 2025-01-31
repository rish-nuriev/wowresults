from django import template
from tournaments.models import Tournament


register = template.Library()


@register.inclusion_tag("tournaments/menu.html")
def show_menu(search_query=""):
    tournaments = Tournament.objects.filter(is_regular=True)
    t_urls = {}
    for t in tournaments[::-1]:
        t_urls[t.title] = t.get_absolute_url()
    return {"tournaments": tournaments, "t_urls": t_urls, "q": search_query}
