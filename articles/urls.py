from django.urls import path, register_converter

from . import views
from . import converters

register_converter(converters.DateConverter, "date")

app_name = "articles"

urlpatterns = [
    path("", views.ArticleListView.as_view(), name="home"),
    path(
        "tag/<slug:tag_slug>",
        views.ArticleListView.as_view(),
        name="articles_list_by_tag",
    ),
    path("articles/create/<date:match_day>", views.create, name="create"),
    path(
        "articles/<slug:t_slug>",
        views.ArticlesByTournament.as_view(),
        name="articles_by_tournament",
    ),
    path("search/", views.post_search, name="post_search"),
    path("<slug:article_slug>/", views.ShowArticle.as_view(), name="article"),
]
