from django.contrib import admin

from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    fields = ["title", "slug", "content"]
    prepopulated_fields = {"slug": ("title",)}

    list_display = (
        "title",
        "match_day",
        "time_create",
        "is_published",
        "tournament",
    )
    list_editable = ("is_published",)
