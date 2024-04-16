from django.contrib import admin

from .models import Article

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    fields = ["title", "slug", "content"]
    prepopulated_fields = {"slug": ("title",)}
