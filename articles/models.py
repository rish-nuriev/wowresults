from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from taggit.managers import TaggableManager
from taggit.models import TagBase, GenericTaggedItemBase

from tournaments.models import Tournament

def translit_to_eng(s: str) -> str:
    d = {'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
         'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i', 'к': 'k',
         'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
         'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch',
         'ш': 'sh', 'щ': 'shch', 'ь': '', 'ы': 'y', 'ъ': '', 'э': 'r', 'ю': 'yu', 'я': 'ya'}

    return "".join(map(lambda x: d[x] if d.get(x, False) else x, s.lower()))


class TranslitTag(TagBase):
    def slugify(self, tag, i=None):
        slug = super().slugify(tag, i)
        return slugify(translit_to_eng(slug))

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
        return reverse("article", kwargs={"article_slug": self.slug})
