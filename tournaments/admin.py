from typing import Any
from django.contrib import admin
from django.db.models.query import QuerySet
from django.db import models
from django.http.request import HttpRequest

from tournaments.widgets import CustomDatePickerInput

from .forms import TeamForm

from .models import Country, Event, Stage, Team, Tournament, Match


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    fields = ["title", "slug"]
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    fields = [
        "title",
        "slug",
        "season",
        "country",
        "league_api_football",
        "season_api_football",
        "current",
        "is_regular",
        "tours_count",
        "logo",
        "order",
    ]
    prepopulated_fields = {"slug": ("title", "season")}
    list_display = (
        "title",
        "season",
        "country",
        "current",
        "is_regular",
        "tours_count",
        "order",
    )


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    form = TeamForm
    fields = ["title", "city", "slug", "country", "id_api_football", "is_moderated"]
    prepopulated_fields = {"slug": ("title", "city")}
    list_display = ("title", "city", "slug", "country", "is_moderated")
    list_filter = ["country", "is_moderated"]


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    fields = ["title"]
    list_display = ("title",)


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    fields = [
        "tournament",
        "date",
        "tour",
        "stage",
        "main_team",
        "opponent",
        "goals_scored",
        "goals_conceded",
        "group",
        "status",
        "is_moderated",
        "score",
        "id_api_football",
        "video",
    ]
    list_display = (
        "tournament",
        "date",
        "tour",
        "stage",
        "main_team",
        "opponent",
        "goals_scored",
        "goals_conceded",
        "group",
        "status",
        "is_moderated",
        "id_api_football",
    )

    list_filter = ["tournament", "stage", "status"]
    formfield_overrides = {models.DateField: {"widget": CustomDatePickerInput}}
    search_fields = ["main_team__title", "opponent__title"]

    ordering = ["date", "id"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return Match.main_matches


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    # fields = '__all__'
    list_display = ("title", "tournament", "team", "operation", "value", "tour")
