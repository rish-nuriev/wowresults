from django.urls import path, register_converter

from . import views
from . import converters

register_converter(converters.DateConverter, "date")

urlpatterns = [
    path('create/<date:match_day>', views.create, name="create"),
    # path('<slug:article_slug>/', views.ShowArticle.as_view(), name='article'),
]
