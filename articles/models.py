import random
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from taggit.managers import TaggableManager
from taggit.models import TagBase, GenericTaggedItemBase
from articles.helpers import translit_to_eng
from tournaments.models import Tournament


class TranslitTag(TagBase):
    def slugify(self, tag, i=None):
        slug = super().slugify(tag, i)
        return slugify(translit_to_eng(slug))

    def get_absolute_url(self):
        return reverse("articles:articles_list_by_tag", kwargs={"tag_slug": self.slug})

    @classmethod
    def get_random_tags(cls, tags_number=5):
        # Джанго позволяет получить случайные записи
        # вот так - cls.objects.order_by("?")[:tags_number]
        # но в случае увеличения кол-ва тегов в БД
        # нагрузка на БД будет возрастать
        # поэтому лучше использовать random
        all_tags = list(cls.objects.all())
        random.shuffle(all_tags)

        return all_tags[:tags_number]


class TaggedWithTranslitTag(GenericTaggedItemBase):
    tag = models.ForeignKey(
        TranslitTag,
        on_delete=models.CASCADE,
        related_name="translittag_items",
    )


class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_published=Article.Status.PUBLISHED)


class Article(models.Model):

    tags = TaggableManager(through=TaggedWithTranslitTag)

    class Status(models.IntegerChoices):
        DRAFT = 0, "Черновик"
        PUBLISHED = 1, "Опубликовано"

    title = models.CharField(max_length=255, verbose_name="Заголовок")
    slug = models.SlugField(
        max_length=255, unique=True, db_index=True, verbose_name="Slug"
    )
    content = models.TextField(blank=True, verbose_name="Генерируемый текст статьи")
    additional_content = models.TextField(
        blank=True, null=True, verbose_name="Дополнительный текст"
    )

    time_create = models.DateTimeField(auto_now_add=True, verbose_name="Время создания")
    time_update = models.DateTimeField(auto_now=True, verbose_name="Время изменения")
    is_published = models.BooleanField(
        choices=tuple(map(lambda x: (bool(x[0]), x[1]), Status.choices)),
        default=Status.DRAFT,
        verbose_name="Статус",
    )
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.PROTECT,
        related_name="posts",
        verbose_name="Турнир",
        null=True,
        blank=True,
    )
    match_day = models.DateField(verbose_name="Игровой день", blank=True, null=True)

    objects = models.Manager()
    published = PublishedManager()

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Статья"
        verbose_name_plural = "Статьи"
        ordering = ["-time_create"]
        indexes = [models.Index(fields=["-time_create"])]

    def get_absolute_url(self):
        return reverse("articles:article", kwargs={"article_slug": self.slug})


class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["created"]
        indexes = [
            models.Index(fields=["created"]),
        ]

    def __str__(self):
        return f"Комментарий от {self.author.username} к {self.article}"
