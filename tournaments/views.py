from datetime import datetime, timezone

import logging
from django.http import HttpResponse, HttpResponseNotFound, Http404
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import (
    authentication_classes,
    permission_classes,
    api_view,
)

from tournaments import tasks
from tournaments.tools import api_tools
import tournaments.models as t_models


logger = logging.getLogger("basic_logger")


MAX_REQUESTS_COUNT = api_tools.get_max_requests_count()


class MatchesByTournament(ListView):
    """
    Отображение списка матчей определенного турнира
    """

    template_name = "tournaments/tournament.html"
    context_object_name = "matches"
    title_page = "Матчи турнира"

    def get_queryset(self):
        # получаем список основных матчей (at_home=True)
        # если передан тур, показываем только матчи тура
        queryset = t_models.Match.main_matches.select_related(
            "main_team", "opponent", "tournament"
        ).filter(tournament__slug=self.kwargs["t_slug"])
        if self.kwargs.get("tour"):
            queryset = queryset.filter(tour=self.kwargs["tour"])
        if not queryset:
            raise Http404
        return queryset.order_by("-tour", "date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = t_models.Tournament.objects.prefetch_related("events").get(
            slug=self.kwargs["t_slug"]
        )
        context["statuses"] = t_models.Match.get_statuses_as_dict()
        context["tournament"] = tournament
        context["tours_range"] = range(1, tournament.tours_count + 1)
        context.update(self.kwargs)
        return context


class ShowMatch(DetailView):
    template_name = "tournaments/match.html"
    context_object_name = "match"

    def get_object(self, queryset=None):
        return get_object_or_404(t_models.Match, pk=self.kwargs["match_id"])


def page_not_found(request, exception):
    return HttpResponseNotFound("<h1>Страница не найдена</h1>")


@permission_classes((IsAuthenticated,))
@authentication_classes((JWTAuthentication,))
@api_view(["GET"])
def get_results(request, process_date="", current=True):
    """
    Метод запрашивает результаты матчей через АПИ.
    И далее записывает результаты в базу данных.
    По умолчанию выбирается текущая дата и обновляются результаты текущих турниров.
    То есть турниры по умолчанию фильтруются по полю current=True.
    Если же передана дата то будут обрабатываться матчи именно на ту дату.
    Если параметр current приходит как False,
    то уже будут обрабатываться недействующие турниры.
    Сезон будет выбран на основании даты.
    Берется год и проверяется - попадает ли в годы сезона.
    Пока у нас все турниры - это регулярные чемпионаты.
    Но возможно позже будут добавлены кубки, чемпионаты мира и т.п.
    """

    today = datetime.now(timezone.utc).date()

    date_to_check = process_date or today

    api_tools.check_api_requests(MAX_REQUESTS_COUNT)

    tournaments = t_models.Tournament.reg_objects.get_tournaments_by_season(
        date_to_check.year, current=current
    )

    matches = api_tools.request_tournaments_matches_by_date(tournaments, date_to_check)
    matches_to_save = api_tools.prepare_matches_data_for_saving(matches)
    t_models.Match.save_prepared_matches(matches_to_save)

    info_message = (
        f"{date_to_check} has been processed. And it can be processed again if needed"
    )
    logger.info(info_message)
    return HttpResponse(info_message)


@permission_classes((IsAuthenticated,))
@authentication_classes((JWTAuthentication,))
@api_view(["GET"])
def get_teams(request):
    """
    Данный метод создает новые команды а также может обновить данные
    команд созданных этим же АПИ.
    Но нужно понимать что если АПИ поменяется то прежние команды проекта
    можно будет использовать только если вручную прописывать их связи по ID в админке
    Автоматически связать команды не получится (название команды может быть записано по-другому)
    """

    api_tools.check_api_requests(MAX_REQUESTS_COUNT)

    tournaments = t_models.Tournament.objects.filter(pk=17)

    teams_by_country = api_tools.request_teams_by_tournaments(tournaments)
    teams_data = api_tools.prepare_teams_data_for_saving(teams_by_country)
    teams_to_save, teams_to_add_logo = teams_data

    tasks.async_save_raw_teams.delay(teams_to_save)
    tasks.async_save_multiple_logos.delay(teams_to_add_logo)

    return HttpResponse("Request completed")


@permission_classes((IsAuthenticated,))
@authentication_classes((JWTAuthentication,))
@api_view(["GET"])
def get_goals_stats(request):

    api_tools.check_api_requests(MAX_REQUESTS_COUNT)

    matches = t_models.Match.main_matches.get_matches_to_update_stats()

    if not matches:
        return HttpResponse("No matches to update goals stats")

    matches_stats = api_tools.request_stats_for_matches(matches)

    if matches_stats is None:
        return HttpResponse("Response Errors: please check the logs for details")

    t_models.Match.update_goals_stats_for_matches(matches_stats)

    logger.info("get_goals_stats request has been completed")
    return HttpResponse("Request has been completed")
