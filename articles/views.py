import logging
from django.conf import settings
from django.contrib import messages
from django.db import connection
from django.db.models import Q, Prefetch
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.utils.text import slugify
from django.views.generic import DetailView, ListView
from django.views.decorators.http import require_POST
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.admin.views.decorators import staff_member_required

from articles.tools import (
    ArticleGenerationError,
    generate_article_tags,
    generate_content_from_template,
    generate_title,
    get_nice_formatted_date,
)
from articles.helpers import translit_to_eng
from articles.models import Article, Comment, TranslitTag

from tournaments.models import Match
from .forms import CommentForm, SearchForm

logger = logging.getLogger("basic_logger")

@staff_member_required
def create(request, match_day):
    tournaments_to_process = (
        Match.main_matches.values(
            "tournament__id", "tournament__title", "tournament__season"
        )
        .filter(date__contains=match_day)
        .distinct()
    )

    for tournament in tournaments_to_process:
        # сразу преобразуем QuerySet в список чтобы
        # избежать повторных запросов в бд
        matches = list(Match.main_matches.filter(
            tournament=tournament["tournament__id"],
            status=Match.Statuses.FULL_TIME,
            date__contains=match_day,
        ))

        nice_date = get_nice_formatted_date(match_day)
        title = generate_title(nice_date, tournament)
        try:
            content = generate_content_from_template(
                "custom_templates/article_text.html", nice_date, matches
            )
        except ArticleGenerationError as e:
            logger.error(e)
            return HttpResponse("Errors during articles generation. \
                                 Please check the logs")

        tags = generate_article_tags(nice_date, matches, tournament)

        slug = slugify(translit_to_eng(title))

        defaults = {
            "title": title,
            "slug": slug,
            "content": content,
            "tournament_id": tournament["tournament__id"],
            "match_day": match_day,
            "is_published": True,
        }

        # На данный момент просто сохраняю статью,
        # хотя вариант с обновлением статьи также работает,
        # просто решил не дергать бд каждый раз
        # но возможно потребуется включить подготовив create_defaults
        # Article.objects.update_or_create(slug=slug, defaults=defaults, create_defaults=create_defaults)
        article, created = Article.objects.get_or_create(slug=slug, defaults=defaults)
        for tag in tags:
            article.tags.add(tag)
        article.save()

    return HttpResponse(f"All the articles for {match_day} have been created/updated")


class ShowArticle(DetailView):
    template_name = "articles/article.html"
    context_object_name = "article"

    def get_object(self, queryset=None):
        # Определяем QuerySet для фильтрации комментариев
        filtered_comments = Comment.objects.select_related("author").filter(active=True)
        return get_object_or_404(
            Article.objects.prefetch_related(
                Prefetch("comments", queryset=filtered_comments)
            ),
            slug=self.kwargs["article_slug"],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = CommentForm()
        context["form"] = form
        context["comments"] = form
        context.update(kwargs)
        return context


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
        "cbv": True,
    }


class ArticlesByTournament(ListView):
    template_name = "articles/list.html"
    context_object_name = "posts"
    allow_empty = False
    paginate_by = 5

    def get_queryset(self):
        return Article.published.filter(
            tournament__slug=self.kwargs["t_slug"]
        ).select_related("tournament")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = context["posts"][0].tournament
        context["tournament"] = tournament
        context["cbv"] = True
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


@require_POST
def post_comment(request, article_id):
    article = get_object_or_404(
        Article, id=article_id, is_published=Article.Status.PUBLISHED
    )
    comment = None
    # Комментарий был отправлен
    form = CommentForm(data=request.POST)
    if form.is_valid():
        # Создать объект класса Comment, не сохраняя его в базе данных
        comment = form.save(commit=False)
        # Назначить статью комментарию
        comment.article = article
        # Назначить автора
        comment.author = request.user
        # Сохранить комментарий в базе данных
        comment.save()
        messages.success(request, "Комментарий успешно добавлен")
    else:
        messages.error(request, "Ошибка! Пожалуйста свяжитесь с администратором")
    return redirect(article)
