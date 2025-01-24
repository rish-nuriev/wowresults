from __future__ import annotations
from datetime import datetime
import logging
from typing import Any, Optional, Self, TypeVar
from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify
import django.utils.timezone
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from tournaments import image_tools


logger = logging.getLogger("basic_logger")


class ApiFootballID(models.Model):
    """
    Модели проекта не должны зависеть от модели АПИ напрямую
    Поэтому связываю их через GenericForeignKey
    И при этом нельзя использовать GenericRelation
    Все запросы будут идти через связывающую модель ContentType
    Также нужно учесть что т.к. GenericRelation не определено
    то в случае удаления Команды например, удаление из данной таблицы
    не происходит автоматически а реализовано в match_pre_delete_handler
    """

    api_football_id = models.PositiveIntegerField(null=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    def __str__(self) -> str:
        return f"{self.api_football_id} - ({self.content_type}) - {self.content_object}"

    class Meta:
        unique_together = ("content_type", "object_id", "api_football_id")
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]
        verbose_name = "Соответствия APIFootball"
        verbose_name_plural = "Соответствие APIFootball"

    @classmethod
    def get_team_by_api_id(cls, team_id_from_api: int) -> Team | None:
        team_ct = ContentType.objects.get_for_model(Team)
        api_obj = cls.objects.filter(
            content_type=team_ct, api_football_id=team_id_from_api
        ).first()
        team: Optional[Team] = None

        if not api_obj:
            warning_msg = f"get_team_by_api_id method: {api_obj} \
                           is missing for team_id_from_api-{team_id_from_api}"
            logger.warning(warning_msg)
        else:
            team = api_obj.content_object
        return team

    @classmethod
    def get_tournament_api_obj_by_tournament(
        cls, tournament: Tournament
    ) -> Self | None:
        tournament_ct = ContentType.objects.get_for_model(Tournament)
        return cls.objects.filter(
            content_type=tournament_ct, object_id=tournament.id
        ).first()

    @classmethod
    def get_match_record(cls, match_id: int) -> Self | None:
        match_ct = ContentType.objects.get_for_model(Match)
        return cls.objects.filter(
            content_type=match_ct, api_football_id=match_id
        ).first()

    @classmethod
    def get_api_match_record_by_match_obj(cls, match_obj: Match) -> Self | None:
        match_ct = ContentType.objects.get_for_model(Match)
        return cls.objects.filter(content_type=match_ct, object_id=match_obj.id).first()

    @classmethod
    def get_team_record(cls, team_id: int) -> Self | None:
        team_ct = ContentType.objects.get_for_model(Team)
        return cls.objects.filter(content_type=team_ct, api_football_id=team_id).first()

    @staticmethod
    def get_tournament_api_season_by_tournament(tournament: Tournament) -> str:
        return tournament.season.split("-")[0]


class ApiModelMixin:
    main_api_model = globals()[settings.MAIN_API_MODEL]()


M = TypeVar("M", bound=models.Model)


class MainMatchesManager(models.Manager[M]):
    """
    Кастомный менеджер для модели Match.
    Возвращает по умолчанию только матчи сыгранные дома (главные).
    Это необходимо чтобы исключить дубликаты.
    Так как каждый матч записывается в базу в 2 экземплярах:
    первый - для команды играющей дома,
    второй - для команды на выезде
    """

    def get_queryset(self) -> models.QuerySet[M]:
        return (
            super()
            .get_queryset()
            .select_related("main_team", "opponent", "tournament")
            .filter(at_home=True)
        )

    def get_matches_by_date(self, date: datetime) -> models.QuerySet[M]:
        """Выборка матчей на определенную дату"""
        return self.get_queryset().filter(date__date=date)

    def get_matches_to_update_stats(self) -> models.QuerySet[M]:
        """Выборка 10 завершившихся матчей с незаполненной статистикой"""
        return (
            self.get_queryset()
            .filter(
                status=Match.Statuses.FULL_TIME,
                goals_stats__isnull=True,
            )
            .select_related("main_team", "opponent")
            .order_by("-id")[:10]
        )


class RegularTournamentsManager(models.Manager[M]):
    """
    Кастомный менеджер для модели Tournament.
    Возвращает по умолчанию только регулярные турниры (Чемпионаты).
    """

    def get_queryset(self) -> models.QuerySet[M]:
        return super().get_queryset().filter(is_regular=True)

    def get_tournaments_by_season(
        self, season: str, current: bool = True
    ) -> models.QuerySet[M]:
        """
        Выборка турниров по сезону.
        current=True вернет именно действующие турниры
        """
        return self.get_queryset().filter(season__contains=season, current=current)


class Tournament(models.Model):
    title = models.CharField(max_length=255, db_index=True, verbose_name="Турнир")
    slug = models.SlugField(max_length=255, unique=True)
    season = models.CharField(max_length=100, verbose_name="Сезон")
    league_api_football = models.BigIntegerField(
        db_index=True, verbose_name="Лига на API Football", default=0
    )
    season_api_football = models.CharField(
        max_length=100, verbose_name="Сезон на API Football", default=0
    )
    description = models.TextField(blank=True, verbose_name="Описание турнира")
    country = models.ForeignKey(
        "Country",
        on_delete=models.PROTECT,
        related_name="tournaments",
        verbose_name="Страна",
    )
    current = models.BooleanField(default=False, verbose_name="Действующий")
    is_regular = models.BooleanField(default=False, verbose_name="Регулярный чемпионат")
    tours_count = models.IntegerField(
        verbose_name="Количество туров", blank=True, default=0
    )
    points_per_win = models.IntegerField(default=3, verbose_name="Очков за победу")
    points_per_draw = models.IntegerField(default=1, verbose_name="Очков за ничью")
    order = models.IntegerField(default=1, verbose_name="Порядок", db_index=True)
    logo = models.ImageField(upload_to="images/tournaments/", null=True)

    class Meta:
        verbose_name = "Турнир"
        verbose_name_plural = "Турниры"
        ordering = ["order", "-season"]

    objects = models.Manager()
    reg_objects = RegularTournamentsManager()

    def __str__(self) -> str:
        return f"{self.title} - {self.season}"

    def get_absolute_url(self) -> str:
        return reverse("tournament", kwargs={"t_slug": self.slug})

    def get_articles_url(self) -> str:
        return reverse("articles:articles_by_tournament", kwargs={"t_slug": self.slug})


class Country(models.Model):
    title = models.CharField(max_length=255, db_index=True, verbose_name="Страна")
    slug = models.SlugField(max_length=255, unique=True)

    class Meta:
        verbose_name = "Страна"
        verbose_name_plural = "Страны"

    def __str__(self) -> str:
        return self.title


class Team(models.Model):
    title = models.CharField(max_length=255, db_index=True, verbose_name="Название")
    slug = models.SlugField(max_length=255, unique=True)
    city = models.CharField(max_length=255, verbose_name="Город")
    id_api_football = models.BigIntegerField(
        db_index=True, verbose_name="ID на API Football", default=0
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="teams",
        verbose_name="Страна",
    )
    is_moderated = models.BooleanField(default=True, verbose_name="Проверка пройдена")
    logo = models.ImageField(upload_to="images/teams/", null=True)
    temporary_team_id = models.IntegerField(
        blank=True,
        null=True,
        default=0,
        verbose_name="Поле для хранения временного ID от АПИ",
    )

    class Meta:
        verbose_name = "Команда"
        verbose_name_plural = "Команды"
        ordering = ["title"]

    def save(self, *args, **kwargs):  # type: ignore
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title

    @classmethod
    def save_raw_teams(cls, teams: list[tuple[int, str, int, str]]) -> None:
        for team_id, team_name, country_id, team_logo in teams:
            team_obj = cls.objects.create(
                temporary_team_id=team_id,
                title=team_name,
                country_id=country_id,
                city=team_name,
                is_moderated=False,  # False потому что нужно скорректировать город и название
            )
            if team_logo:
                team_obj.save_logo(team_logo)

    @classmethod
    def save_multiple_logos(cls, teams: list[tuple[Team, str]]) -> None:
        for team_obj, team_logo in teams:
            team_obj.save_logo(team_logo)

    def save_logo(self, logo_url: str) -> None:
        logo_data = image_tools.download_logo(logo_url)
        if logo_data:
            file_name, file = logo_data
            self.logo.save(file_name, file)


class Match(models.Model, ApiModelMixin):

    class ResultVals(models.TextChoices):
        WIN = "W", "Победа"
        DRAW = "D", "Ничья"
        LOSE = "L", "Поражение"

    class Statuses(models.TextChoices):
        NOT_STARTED = "NS", "Не начался"
        FULL_TIME = "FT", "Завершен"
        FIRST_HALF = "1H", "Идет первый тайм"
        HALFTIME = "HT", "Перерыв"
        SECOND_HALF = "2H", "Идет второй тайм"
        CANCELLED = "CANC", "Отменен"
        PENALTY = "PEN", "Серия пенальти"
        TOBEDEFINED = "TBD", "Точная дата не известна"
        POSTPONED = "PST", "Отложен"
        INTERRUPTED = "INT", "Прерван"

    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.PROTECT,
        related_name="matches",
        verbose_name="Турнир",
    )
    stage = models.ForeignKey(
        "Stage",
        on_delete=models.PROTECT,
        verbose_name="Стадия турнира",
        blank=True,
        null=True,
        default=None,
    )
    group = models.CharField(max_length=2, verbose_name="Группа", blank=True, null=True)
    tour = models.IntegerField(blank=True, null=True, default=0, verbose_name="Тур")
    temporary_match_id = models.IntegerField(
        blank=True,
        null=True,
        default=0,
        verbose_name="Поле для хранения временного ID от АПИ",
    )
    date = models.DateTimeField(
        default=django.utils.timezone.now, verbose_name="Дата и время"
    )
    main_team = models.ForeignKey(
        "Team",
        on_delete=models.PROTECT,
        related_name="matches",
        verbose_name="Команда",
    )
    opponent = models.ForeignKey(
        "Team",
        on_delete=models.PROTECT,
        verbose_name="Соперник",
    )
    at_home = models.BooleanField(default=True)
    result = models.CharField(
        max_length=1,
        verbose_name="Результат",
        choices=ResultVals.choices,
        default=ResultVals.WIN,
        null=True,
    )
    status = models.CharField(
        max_length=5,
        verbose_name="Статус матча",
        choices=Statuses.choices,
        default=Statuses.NOT_STARTED,
    )
    points_received = models.IntegerField(default=0, verbose_name="Очков получено")
    goals_scored = models.IntegerField(
        default=0, verbose_name="Голов забито", null=True
    )
    goals_conceded = models.IntegerField(
        default=0, verbose_name="Голов пропущено", null=True
    )
    video = models.CharField(
        max_length=255, verbose_name="Видео", blank=True, null=True
    )
    opposite_match = models.BigIntegerField(default=0, verbose_name="Сопряженный матч")
    score = models.JSONField(default=dict)
    goals_stats = models.JSONField(null=True)
    is_moderated = models.BooleanField(default=True, verbose_name="Проверка пройдена")

    """
        TODO - Добавить функционал доп времени и пенальти соответствующим изменением хендлеров
        Будет флаг is_special - если да то матч закончился необычно
        is_special = models.BooleanField(default=False) # техническое поражение, доп время, пенальти и т.д.
        в result добавится 4 статуса - победа в доп. время, поражение в доп.время, победа по пенальти, поражение по пенальти
        points_received в этом случае прописывается отдельно, становится обязательным
        соответственно доп поля: 
        extra_goals_scored (голов забито учитывая доп время)
        extra_goals_conceded (голов пропущено учитывая доп время)
        pen_goals_scored (голов забито по пенальти)
        pen_goals_conceded (голов пропущено по пенальти)
    """

    class Meta:
        verbose_name = "Матч"
        verbose_name_plural = "Матчи"
        unique_together = ("main_team", "opponent", "date")

    objects = models.Manager()
    main_matches = MainMatchesManager()

    def __str__(self) -> str:
        return f"{self.main_team.title} - {self.opponent.title}"

    def get_absolute_url(self) -> str:
        return reverse(
            "match",
            kwargs={
                "t_slug": self.tournament.slug,
                "tour": self.tour,
                "match_id": self.id,
            },
        )

    def update_goals_stats(self, goals_stats: dict[int, dict[str, str]]) -> None:
        self.goals_stats = goals_stats
        self.save()

    @classmethod
    def update_goals_stats_for_matches(
        cls, matches: dict[int, dict[int, dict[str, str]]]
    ) -> None:
        for match_id, goals_stats in matches.items():
            match_to_update = cls.objects.get(pk=match_id)
            match_to_update.update_goals_stats(goals_stats)

    @classmethod
    def get_statuses_as_dict(cls) -> dict[str, str]:
        return dict(cls.Statuses.choices)

    @classmethod
    def create_or_update_match(
        cls, team1: Team, team2: Team, match_data: dict[str, Any]
    ) -> None:
        """
        После того как из АПИ получили и обработали данные о матче
        можем либо обновить данные либо создать новый матч
        :param team1: - принимающая команда - объект Team
        :param team2: - гостевая команда - объект Team
        :param match_data: - все обязательные поля модели Match
        match_data["match_id"] - это id матча из АПИ
        через него модель Match связывается с моделью АПИ
        """

        api_match_record = cls.main_api_model.get_match_record(match_data["match_id"])

        if api_match_record:
            match_record = api_match_record.content_object

            # result, points_received определяются в pre_save signals
            data_for_update = {
                "date": match_data["match_date"],
                "status": match_data["status"],
                "goals_scored": match_data["goals_scored"],
                "goals_conceded": match_data["goals_conceded"],
                "is_moderated": match_data["is_moderated"],
                "result": match_record.result,
                "points_received": match_record.points_received,
            }

            for field, value in data_for_update.items():
                setattr(match_record, field, value)

            match_record.save()
        else:
            m = cls()

            m.date = match_data["match_date"]
            m.main_team = team1
            m.opponent = team2
            m.status = match_data["status"]
            m.goals_scored = match_data["goals_scored"]
            m.goals_conceded = match_data["goals_conceded"]
            m.tournament_id = match_data["tournament_id"]
            m.tour = match_data["tour"]
            m.stage = None
            m.is_moderated = match_data["is_moderated"]
            m.score = match_data["score"]
            m.temporary_match_id = match_data["match_id"]
            m.save()

    @classmethod
    def save_prepared_matches(
        cls, matches: list[tuple[Team, Team, dict[str, str]]]
    ) -> None:
        for team1, team2, match_data in matches:
            cls.create_or_update_match(team1, team2, match_data)


class Stage(models.Model):
    title = models.CharField(max_length=255, verbose_name="Стадия турнира")
    title_api_football = models.CharField(
        max_length=255, verbose_name="Стадия турнира на API Football"
    )

    class Meta:
        verbose_name = "Стадия турнира"
        verbose_name_plural = "Стадии турнира"

    def __str__(self) -> str:
        return self.title


class Event(models.Model):

    class Operations(models.TextChoices):
        ADD = "A", "Добавить"
        REMOVE = "R", "Отнять"
        NOTHING = "N", "Не менять"

    title = models.CharField(max_length=255, verbose_name="Событие")
    description = models.TextField(blank=True, verbose_name="Описание события")
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name="Турнир",
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.PROTECT,
        related_name="events",
        verbose_name="Команда",
        blank=True,
        null=True,
    )
    operation = models.CharField(
        max_length=1,
        verbose_name="Операция",
        choices=Operations.choices,
        default=Operations.NOTHING,
    )
    value = models.IntegerField(default=0)
    tour = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Событие"
        verbose_name_plural = "События"
