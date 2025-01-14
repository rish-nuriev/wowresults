from datetime import datetime, timezone
import tempfile

import logging
import requests

from django.core import files
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

from tournaments import api_tools, utils
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

    utils.check_api_requests(MAX_REQUESTS_COUNT)

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

    utils.check_api_requests(MAX_REQUESTS_COUNT)

    endpoint = main_api.get_endpoint("get_teams")

    tournaments = t_models.Tournament.objects.filter(current=True)

    for t in tournaments:

        tournament_api_id = main_api_model.get_tournament_api_id_by_tournament(t)
        tournament_api_season = main_api_model.get_tournament_api_season_by_tournament(
            t
        )

        payload = main_api.get_payload(
            task="get_teams",
            tournament_api_id=tournament_api_id,
            tournament_api_season=tournament_api_season,
        )

        response = main_api.send_request(endpoint, payload)

        if response["errors"]:
            return HttpResponse("Response Errors: please check the logs for details")

        utils.increase_api_requests_count()

        teams = api_parser.parse_teams(response)

        for team in teams:

            team_id = api_parser.get_team_id(team)
            team_name = api_parser.get_team_name(team)
            team_logo = api_parser.get_team_logo(team)

            api_team_record = main_api_model.get_team_record(team_id)

            if api_team_record:
                team_obj = api_team_record.content_object
            else:
                team_obj = t_models.Team.objects.create(
                    title=team_name,
                    country=t.country,
                    city=team_name,
                    is_moderated=False,  # False потому что нужно скорректировать город и название
                )

                api_model_obj = main_api_model.__class__()

                api_model_obj.api_football_id = team_id
                api_model_obj.content_object = team_obj

                api_model_obj.save()

            if not team_obj.logo:
                logo_url = team_logo
                logo_response = requests.get(logo_url, stream=True, timeout=10)
                if logo_response.status_code == requests.codes.ok:
                    file_name = logo_url.split("/")[-1]
                    # Create a temporary file
                    tmp_file = tempfile.NamedTemporaryFile()
                    # Read the streamed image in sections
                    for block in logo_response.iter_content(1024 * 8):
                        # If no more file then stop
                        if not block:
                            break
                        # Write image block to temporary file
                        tmp_file.write(block)
                    # Save the temporary image to the model#
                    # This saves the model so be sure that it is valid
                    team_obj.logo.save(file_name, files.File(tmp_file))

    return HttpResponse("Request completed")


@permission_classes((IsAuthenticated,))
@authentication_classes((JWTAuthentication,))
@api_view(["GET"])
def get_goals_stats(request):

    utils.check_api_requests(MAX_REQUESTS_COUNT)

    matches = t_models.Match.main_matches.get_matches_to_update_stats()

    matches_stats = api_tools.request_stats_for_matches(matches)
    t_models.Match.update_goals_stats_for_matches(matches_stats)

    logger.info("get_goals_stats request has been completed")
    return HttpResponse("Request has been completed")
