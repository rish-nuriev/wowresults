from datetime import datetime, timedelta, timezone
import tempfile
import requests
import redis
from django.core import files

from django.http import HttpResponse, HttpResponseNotFound, Http404
from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView, ListView
from django.conf import settings
from tournaments.apifootball import ApiFootball

from tournaments.models import Match, Stage, Team, Tournament


if settings.LOCAL_MACHINE:
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
        tournament = Tournament.objects.get(slug=self.kwargs["t_slug"])
        context["rtypes"] = Match.ResultVals
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


def home(request):
    return render(request, "tournaments/home.html", {"title": "Главная"})


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


def get_results(request):

    api_football = ApiFootball()

    endpoint = "fixtures"

    tournaments = Tournament.objects.filter(current=True)

    for t in tournaments:

        check_date = datetime(2023, 11, 4)
        end_date = datetime(2023, 11, 4)

        td = timedelta(days=1)

        while check_date <= end_date:

            payload = {
                "league": t.league_api_football,
                "season": t.season_api_football,
                "date": check_date.strftime("%Y-%m-%d"),
            }

            check_date += td

            response = api_football.send_request(endpoint, payload)

            if response["errors"]:
                return HttpResponse(
                    "Response Errors: please check the logs for details"
                )

            matches = response["response"]
            for match in matches:
                team1 = get_or_create_team(t, match, "home")
                team2 = get_or_create_team(t, match, "away")

                tour = 0
                stage = None
                if t.is_regular:
                    tour = int(match["league"]["round"].split(" - ")[1])
                else:
                    stage, created = Stage.objects.get_or_create(
                        title_api_football=match["league"]["round"],
                        defaults={
                            "title": match["league"]["round"],
                        },
                    )

                date = match["fixture"]["date"]

                is_moderated = match["fixture"]["status"]["short"] == "FT"

                Match.objects.update_or_create(
                    id_api_football=match["fixture"]["id"],
                    defaults={
                        "date": date,
                        "status": match["fixture"]["status"]["short"],
                        "goals_scored": match["goals"]["home"],
                        "goals_conceded": match["goals"]["away"],
                        "is_moderated": is_moderated,
                        "result": Match.result,
                        "points_received": Match.points_received,
                    },
                    create_defaults={
                        "date": date,
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

    return HttpResponse("Request has been completed")


def get_teams(request):

    api_football = ApiFootball()

    endpoint = "teams"

    tournaments = Tournament.objects.filter(current=True)

    for t in tournaments:

        payload = {
            "league": t.league_api_football,
            "season": t.season_api_football,
        }

        response = api_football.send_request(endpoint, payload)

        if response["errors"]:
            return HttpResponse("Response Errors: please check the logs for details")

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
        .order_by("-id")[:10]
    )

    date_utc = datetime.now(timezone.utc).strftime("%Y_%m_%d")

    if not r.exists(f"{date_utc}_api_requests_count"):
        r.set(f"{date_utc}_api_requests_count", 0)
        r.expire(f"{date_utc}_api_requests_count", 86400)

    api_requests_count = int(r.get(f"{date_utc}_api_requests_count"))

    if api_requests_count < 100:

        for m in matches:

            payload = {
                "fixture": m.id_api_football,
            }

            response = api_football.send_request(endpoint, payload)

            if response["errors"]:
                return HttpResponse(
                    "Response Errors: please check the logs for details"
                )

            r.incr(f"{date_utc}_api_requests_count", 1)

            events = response["response"]
            goals_stats = {}

            for event in events:
                if event["type"] == "Goal":
                    goals_stats[event["time"]["elapsed"]] = {
                        "team": event["team"]["id"],
                        "player": event["player"]["name"],
                        "type": event["detail"],
                    }

            m.goals_stats = goals_stats
            m.save()
    else:
        return HttpResponse("we have reached the limit of the requests")

    return HttpResponse("Request has been completed")
