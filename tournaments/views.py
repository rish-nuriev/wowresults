from datetime import datetime, timezone
import tempfile
import time
import logging
import requests
import redis

from django.core import files
from django.http import HttpResponse, HttpResponseNotFound, Http404
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView
from django.conf import settings

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import (
    authentication_classes,
    permission_classes,
    api_view,
)

from tournaments.api_list.api_parser import ApiParserError, ApiParsersContainer

import tournaments.models as t_models
import tournaments.api_list.apifootball as api_source

from . import redis_tools

logger = logging.getLogger("basic_logger")


r = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASS,
)
main_api = getattr(api_source, settings.MAIN_API)()
main_api_model = getattr(t_models, settings.MAIN_API_MODEL)()
api_parsers_container = ApiParsersContainer(main_api)
api_parser = api_parsers_container.get_api_parser()
MAX_REQUESTS_COUNT = main_api.get_max_requests_count()


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

    endpoint = main_api.get_endpoint("results_by_tournament")

    today = datetime.now(timezone.utc).date()

    date_to_check = process_date or today
    api_requests_count = redis_tools.get_api_requests_count(r)

    match_options = (
        "match_id",
        "match_date",
        "main_team_id",
        "opponent_id",
        "tour",
        "status",
        "goals_scored",
        "goals_conceded",
        "score",
    )

    if api_requests_count >= MAX_REQUESTS_COUNT:
        logger.error("We have reached the limit of API requests")
        return HttpResponse("we have reached the limit of the requests")

    tournaments = t_models.Tournament.objects.filter(
        current=current, is_regular=True, season__contains=date_to_check.year
    )

    for t in tournaments:

        date = date_to_check.strftime(main_api.DATE_FORMAT)

        tournament_api_obj = main_api_model.get_tournament_api_obj_by_tournament(t)

        if not tournament_api_obj:
            continue

        tournament_api_id = tournament_api_obj.api_football_id
        tournament_api_season = main_api_model.get_tournament_api_season_by_tournament(
            t
        )

        payload = main_api.get_payload(
            task="results_by_tournament",
            tournament_api_id=tournament_api_id,
            tournament_api_season=tournament_api_season,
            date=date,
        )

        response = main_api.send_request(endpoint, payload)

        if response["errors"]:
            return HttpResponse("Response Errors: please check the logs for details")

        redis_tools.increase_api_requests_count(r)

        matches = api_parser.parse_matches(response)

        for match in matches:

            match_data = {}

            for option in match_options:
                try:
                    match_data[option] = getattr(api_parser, "get_" + option)(match)
                except AttributeError:
                    message = f"get_{option} method should be realized in {api_parser.__class__.__name__}"
                    logger.error(message)
                    continue
                except ApiParserError:
                    continue

            team1 = main_api_model.get_team_by_api_id(match_data["main_team_id"])
            team2 = main_api_model.get_team_by_api_id(match_data["opponent_id"])

            if not team1 or not team2:
                # todo We need to add this team into DB using specific API request
                # but not at the same time, the task needs to be added to the queue
                continue

            # поле is_moderated задумывалось как требование ручной корректировки данных
            # в админке т.к. если матч заканчивался по пенальти не было данных из АПИ
            # Решение - купить платный сервис АПИ
            # Пока используем только регулярные чемпионаты поэтому
            # is_moderated можно выставить в True
            is_moderated = True

            api_match_record = main_api_model.get_match_record(match_data["match_id"])

            if api_match_record:
                match_record = api_match_record.content_object

                data_for_update = {
                    "date": match_data["match_date"],
                    "status": match_data["status"],
                    "goals_scored": match_data["goals_scored"],
                    "goals_conceded": match_data["goals_conceded"],
                    "is_moderated": is_moderated,
                    "result": match_record.result,
                    "points_received": match_record.points_received,
                }

                for field, value in data_for_update.items():
                    setattr(match_record, field, value)

                match_record.save()
            else:
                m = t_models.Match()

                m.date = match_data["match_date"]
                m.main_team = team1
                m.opponent = team2
                m.status = match_data["status"]
                m.goals_scored = match_data["goals_scored"]
                m.goals_conceded = match_data["goals_conceded"]
                m.tournament = t
                m.tour = match_data["tour"]
                m.stage = None
                m.is_moderated = is_moderated
                m.score = match_data["score"]
                m.temporary_match_id = match_data["match_id"]
                m.save()

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

    api_requests_count = redis_tools.get_api_requests_count(r)
    if api_requests_count >= MAX_REQUESTS_COUNT:
        logger.error("we have reached the limit of the requests")
        return HttpResponse("we have reached the limit of the requests")

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

        redis_tools.increase_api_requests_count(r)

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

    endpoint = main_api.get_endpoint("get_goals_stats")

    matches = (
        t_models.Match.main_matches.filter(
            status=t_models.Match.Statuses.FULL_TIME,
            goals_stats__isnull=True,
        )
        .select_related("main_team", "opponent")
        .order_by("-id")[:10]
    )

    api_requests_count = redis_tools.get_api_requests_count(r)

    if api_requests_count >= MAX_REQUESTS_COUNT:
        logger.error("we have reached the limit of the requests")
        return HttpResponse("we have reached the limit of the requests")

    for m in matches:

        payload = main_api.get_payload(
            task="get_goals_stats", match_obj=m, main_api_model=main_api_model
        )

        response = main_api.send_request(endpoint, payload)

        if response["errors"]:
            return HttpResponse("Response Errors: please check the logs for details")

        redis_tools.increase_api_requests_count(r)

        goals = api_parser.parse_goals(response)

        goals_stats = api_parser.get_goals_stats(goals)

        m.goals_stats = goals_stats
        m.save()

    logger.info("get_goals_stats request has been completed")
    return HttpResponse("Request has been completed")
