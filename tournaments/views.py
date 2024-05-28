from datetime import datetime, timedelta, timezone
import tempfile
import time
import requests
import redis
from django.core import files

from django.contrib.auth.decorators import permission_required, login_required
from django.http import HttpResponse, HttpResponseNotFound, Http404
from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView, ListView
from django.views.decorators.http import require_POST
from django.conf import settings

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import (
    authentication_classes,
    permission_classes,
    api_view,
)
from rest_framework_simplejwt.authentication import JWTAuthentication

from tournaments.models import Match, Stage, Team, Tournament
from tournaments.apifootball import ApiFootball
from .helpers import *


if settings.LOCAL_MACHINE:
    # Подключаемся к редис только с локальной машины
    # соединить с redis
    r = redis.Redis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB
    )


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
        queryset = Match.main_matches.select_related(
            "main_team", "opponent", "tournament"
        ).filter(tournament__slug=self.kwargs["t_slug"])
        if self.kwargs.get("tour"):
            queryset = queryset.filter(tour=self.kwargs["tour"])
        if not queryset:
            raise Http404
        return queryset.order_by("-tour", "date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = Tournament.objects.prefetch_related("events").get(
            slug=self.kwargs["t_slug"]
        )
        context["statuses"] = dict(Match.Statuses.choices)
        context["tournament"] = tournament
        context["tours_range"] = range(1, tournament.tours_count + 1)
        context.update(self.kwargs)
        return context


class ShowMatch(DetailView):
    template_name = "tournaments/match.html"
    context_object_name = "match"

    def get_object(self, queryset=None):
        return get_object_or_404(Match, pk=self.kwargs["match_id"])


def page_not_found(request, exception):
    return HttpResponseNotFound("<h1>Страница не найдена</h1>")


def get_or_create_team(tournament, match, state):
    team, _ = Team.objects.get_or_create(
        id_api_football=match["teams"][state]["id"],
        defaults={
            "title": match["teams"][state]["name"],
            "country": tournament.country,
            "city": match["teams"][state]["name"],
            "is_moderated": False,
        },
    )
    return team


# @permission_required(["tournaments.add_match", "tournaments.change_match"])
# @permission_classes((IsAuthenticated, ))
# @authentication_classes((JWTAuthentication, ))
# @api_view(['GET'])
def get_results(request, start_date=""):
    """
    Метод запрашивает результаты матчей через ApiFootball и записывает их в базу данных.
    По умолчанию выбирается текущая дата и обновляются результаты текущих турниров.
    То есть турниры по умолчанию фльтруются по полю current=True.
    Если же передана дата то она считается стартовой и проверяется через хранилище Redis.
    Если дата уже была обработана, то берется следующий день и опять проверяется в Redis.
    И так до тех пор пока не найдена необработанная дата либо дата не станет текущей.
    Турнир в таком случае выбирается по принципу сезона.
    И так как сезон вида "2023-2024" то из переданной даты берется год и проверяется - попадает ли в годы сезона.
    Текущая дата в данном случае не обрабатывается.
    """

    if not settings.LOCAL_MACHINE:
        return HttpResponse("This is for local machine only")

    api_football = ApiFootball()

    endpoint = "fixtures"

    today = datetime.now(timezone.utc).date()

    date_to_check = get_date_to_check(r, start_date) if start_date else today
    api_requests_count = get_api_requests_count(r)

    # while date_to_check <= today:
    while True:

        if api_requests_count >= 100:
            return HttpResponse("we have reached the limit of the requests")

        if start_date:
            tournaments = Tournament.objects.filter(
                current=True, is_regular=True, season__contains=date_to_check.year
            )
            print(tournaments)
        else:
            tournaments = Tournament.objects.filter(current=True)

        for t in tournaments:

            payload = {
                "league": t.league_api_football,
                "season": t.season_api_football,
                "date": date_to_check.strftime("%Y-%m-%d"),
            }

            response = api_football.send_request(endpoint, payload)

            if response["errors"]:
                return HttpResponse(
                    "Response Errors: please check the logs for details"
                )

            increase_api_requests_count(r)
            api_requests_count += 1
            matches = response["response"]
            for match in matches:
                team1 = get_or_create_team(t, match, "home")
                team2 = get_or_create_team(t, match, "away")

                tour = 0
                stage = None
                if t.is_regular:
                    try:
                        tour = int(match["league"]["round"].split(" - ")[1])
                    except IndexError:
                        print("The match is out of regular")
                else:
                    stage, created = Stage.objects.get_or_create(
                        title_api_football=match["league"]["round"],
                        defaults={
                            "title": match["league"]["round"],
                        },
                    )

                match_date = match["fixture"]["date"]

                is_moderated = match["fixture"]["status"]["short"] == "FT"

                Match.objects.update_or_create(
                    id_api_football=match["fixture"]["id"],
                    defaults={
                        "date": match_date,
                        "status": match["fixture"]["status"]["short"],
                        "goals_scored": match["goals"]["home"],
                        "goals_conceded": match["goals"]["away"],
                        "is_moderated": is_moderated,
                        "result": Match.result,
                        "points_received": Match.points_received,
                    },
                    create_defaults={
                        "date": match_date,
                        "main_team": team1,
                        "opponent": team2,
                        "status": match["fixture"]["status"]["short"],
                        "goals_scored": match["goals"]["home"],
                        "goals_conceded": match["goals"]["away"],
                        "tournament": t,
                        "tour": tour,
                        "stage": stage,
                        "is_moderated": is_moderated,
                        "score": match["score"],
                    },
                )

        print("Processed date", date_to_check)

        # запросы к текущей и будущей дате могут выполняться многократно, поэтому не маркируем
        if date_to_check < today:
            set_date_processed(r, date_to_check)
        else:
            print(f"{date_to_check} has been processed. And it can be processed again if needed")
            return HttpResponse(
                f"{date_to_check} has been processed. And it can be processed again if needed"
            )

        date_to_check = get_date_to_check(r, date_to_check)
        time.sleep(60)

        # Код поправлен с целью обрабатывать даты в будущем,
        # но пока допустим лишь один запрос к конкретной дате
        if date_to_check > today:
            break

    return HttpResponse("All requests have been completed")


# @require_POST
# @permission_required(["tournaments.add_team", "tournaments.change_team"])
def get_teams(request):

    if not settings.LOCAL_MACHINE:
        return HttpResponse("This is for local machine only")

    api_requests_count = get_api_requests_count(r)
    if api_requests_count >= 100:
        return HttpResponse("we have reached the limit of the requests")

    api_football = ApiFootball()

    endpoint = "teams"

    tournaments = Tournament.objects.filter(current=True)

    print(tournaments)

    for t in tournaments:

        payload = {
            "league": t.league_api_football,
            "season": t.season_api_football,
        }

        response = api_football.send_request(endpoint, payload)

        if response["errors"]:
            return HttpResponse("Response Errors: please check the logs for details")

        increase_api_requests_count(r)

        teams = response["response"]

        for team in teams:
            team_obj, created = Team.objects.get_or_create(
                id_api_football=team["team"]["id"],
                defaults={
                    "title": team["team"]["name"],
                    "country": t.country,
                    "city": team["team"]["name"],
                    "is_moderated": False,
                },
            )
            if not team_obj.logo:
                logo_url = team["team"]["logo"]
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


# @require_POST
# @permission_required(["tournaments.change_match"])
def get_goals_stats(request):

    if not settings.LOCAL_MACHINE:
        return HttpResponse("This is for local machine only")

    api_football = ApiFootball()

    endpoint = "fixtures/events"

    matches = (
        Match.objects.filter(
            at_home=True,
            status=Match.Statuses.FULL_TIME,
            goals_stats__isnull=True,
        )
        .select_related("main_team", "opponent")
        .order_by("id")[:10]
    )

    print(matches)

    api_requests_count = get_api_requests_count(r)

    if api_requests_count >= 100:
        return HttpResponse("we have reached the limit of the requests")

    for m in matches:

        payload = {
            "fixture": m.id_api_football,
        }

        response = api_football.send_request(endpoint, payload)

        if response["errors"]:
            return HttpResponse("Response Errors: please check the logs for details")

        increase_api_requests_count(r)

        events = response["response"]
        goals_stats = {}

        for event in events:
            if event["type"] == "Goal":
                minute = event["time"]["elapsed"]
                if event["time"]["extra"]:
                    minute += event["time"]["extra"]
                goals_stats[minute] = {
                    "team": event["team"]["id"],
                    "player": event["player"]["name"],
                    "type": event["detail"],
                }

        m.goals_stats = goals_stats
        m.save()

    return HttpResponse("Request has been completed")
