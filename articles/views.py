from django.conf import settings
from django.db import connection
from django.db.models import Q
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.core.paginator import Paginator
from django.utils import dateformat
from django.utils.text import slugify
from django.views.generic import DetailView, ListView
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

from articles.helpers import gen_match_text
from articles.models import Article, TranslitTag

from tournaments.models import Match
from .forms import SearchForm


def translit_to_eng(s: str) -> str:
    d = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "yo",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "c",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ь": "",
        "ы": "y",
        "ъ": "",
        "э": "r",
        "ю": "yu",
        "я": "ya",
    }

    return "".join(map(lambda x: d[x] if d.get(x, False) else x, s.lower()))


@login_required
def create(request, match_day):
    tournaments_to_process = (
        Match.main_matches.values(
            "tournament__id", "tournament__title", "tournament__season"
        )
        .filter(date__contains=match_day)
        .distinct()
    )

    for tournament in tournaments_to_process:
        matches = Match.main_matches.filter(
            tournament=tournament["tournament__id"],
            status=Match.Statuses.FULL_TIME,
            date__contains=match_day,
        )
        nice_date = dateformat.format(match_day, settings.DATE_FORMAT)
        title = f'Результаты матчей: {tournament["tournament__title"]} {tournament["tournament__season"]} - {nice_date}'

        content = '<div class="article_wrapper">'
        content += f'<div class="results_description">{nice_date} '

        tags = []

        for match in matches:
            tags.extend([match.main_team.title, match.opponent.title])
            content += gen_match_text(
                match.main_team,
                match.opponent,
                match.result,
                match.goals_scored,
                match.goals_conceded,
            )

        tags.extend(
            [
                tournament["tournament__title"],
                f"матчи {nice_date}",
                f'{tournament["tournament__title"]} {tournament["tournament__season"]} {match.tour} тур',
            ]
        )

        content += "</div>"
        content += (
            "<h3>Предлагаем вашему вниманию результаты завершившихся матчей:</h3>"
        )

        content += "<ul>"
        for match in matches:
            content += f"<li><a href='{ match.get_absolute_url() }'>{ match.main_team }-{ match.opponent } : { match.goals_scored } - { match.goals_conceded }</a></li>"
        content += "</ul>"

        content += "<p>Текст статьи обновляется</p>"

        content += "</div>"

        slug = slugify(translit_to_eng(title))

        defaults = {
            "title": title,
            "slug": slug,
            "content": content,
            "tournament_id": tournament["tournament__id"],
            "match_day": match_day,
            "is_published": True,
        }

        article, created = Article.objects.get_or_create(slug=slug, defaults=defaults)
        for tag in tags:
            article.tags.add(tag)
        article.save()

        # Article.objects.update_or_create(slug=slug, defaults=defaults, create_defaults=create_defaults)

    return HttpResponse(f"All the articles for {match_day} have been created/updated")


class ShowArticle(DetailView):
    template_name = "articles/article.html"
    context_object_name = "article"

    def get_object(self, queryset=None):
        return get_object_or_404(Article, slug=self.kwargs["article_slug"])


class ArticleListView(ListView):
    """
    Представление списка постов
    """

    # По умолчанию берем все статьи
    # Но если передан тег, то фильтруем по тегам
    def get_queryset(self):
        queryset = Article.published.select_related("tournament")
        if self.kwargs.get("tag_slug"):
            tag = get_object_or_404(TranslitTag, slug=self.kwargs["tag_slug"])
            queryset = queryset.filter(tags__in=[tag])
        return queryset

    context_object_name = "posts"
    paginate_by = 5
    template_name = "articles/list.html"

    extra_context = {
        "default_image": settings.DEFAULT_POST_IMAGE,
    }


class ArticlesByTournament(ListView):
    template_name = "articles/list.html"
    context_object_name = "posts"
    allow_empty = False

    def get_queryset(self):
        return Article.published.filter(
            tournament__slug=self.kwargs["t_slug"]
        ).select_related("tournament")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = context["posts"][0].tournament
        context["tournament"] = tournament
        context.update(kwargs)
        return context


def post_search(request):
    """
    Метод реализующий поиск по статьям.
    Если в качестве движка БД используется postgresql
    применяется полнотекстовый поисковый движок иначе
    вхождение поискового запроса в заголовок 
    либо текст статьи.
    """
    form = SearchForm()
    query = None
    posts = []
    if "query" in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data["query"]
            if connection.vendor == "postgresql":
                search_vector = SearchVector("title", "content", config="russian")
                search_query = SearchQuery(query, config="russian")
                posts_list = (
                    Article.published.annotate(
                        search=search_vector,
                        rank=SearchRank(search_vector, search_query),
                    )
                    .filter(search=search_query)
                    .order_by("-rank")
                )
            else:
                posts_list = Article.published.filter(
                    Q(title__icontains=query) | Q(content__icontains=query)
                )
            paginator = Paginator(posts_list, 5)
            page_number = request.GET.get("page", 1)
            posts = paginator.page(page_number)
    return render(
        request,
        "articles/list.html",
        {"paginator": paginator, "query": query, "posts": posts},
    )
