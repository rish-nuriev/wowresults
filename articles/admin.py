from django.contrib import admin

from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    fields = ["title", "slug", "content", "additional_content","is_published","tags"]
    prepopulated_fields = {"slug": ("title",)}

    list_display = (
        "title",
        "match_day",
        "time_create",
        "is_published",
        "tournament",
        "tag_list",
    )
    list_editable = ("is_published",)
    readonly_fields = ('content',)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")

    def tag_list(self, obj):
        return list(obj.tags.all())

    tag_list.short_description = "Теги"
