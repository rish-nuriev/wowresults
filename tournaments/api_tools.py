import logging
from django.conf import settings
from django.http import HttpResponse
from tournaments.api_list.api_parsers import ApiParserError, ApiParsersContainer
from tournaments import models, redis_tools
from tournaments.tasks import async_error_logging
import tournaments.api_list.api_classes as api_source


main_api = getattr(api_source, settings.MAIN_API)()
main_api_model = getattr(models, settings.MAIN_API_MODEL)()
api_parsers_container = ApiParsersContainer(main_api)
api_parser = api_parsers_container.get_api_parser()
logger = logging.getLogger("basic_logger")
REDIS_CONNECTION = redis_tools.get_redis_connection()


def get_max_requests_count():
    return main_api.get_max_requests_count()


def request_tournaments_matches_by_date(tournaments, date_to_check) -> dict:

    endpoint = main_api.get_endpoint("results_by_tournament")
    date = date_to_check.strftime(main_api.DATE_FORMAT)

    matches = {}

    for t in tournaments:

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

        increase_api_requests_count()

        response = main_api.send_request(endpoint, payload)

        if response["errors"]:
            return HttpResponse("Response Errors: please check the logs for details")

        matches[t.id] = api_parser.parse_matches(response)

    return matches


def prepare_matches_data_for_saving(tournament_matches: dict):

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

    matches_to_save = []

    for tournament_id, matches in tournament_matches.items():

        for match in matches:

            match_data = {}

            for option in match_options:
                try:
                    match_data[option] = getattr(api_parser, "get_" + option)(match)
                except AttributeError:
                    message = f"get_{option} method should be realized in {api_parser.__class__.__name__}"
                    logger.error(message)
                    return HttpResponse("Errors: please check the logs for details")
                except ApiParserError as e:
                    logger.error(e)
                    return HttpResponse("Errors: please check the logs for details")

            team1 = main_api_model.get_team_by_api_id(match_data["main_team_id"])
            team2 = main_api_model.get_team_by_api_id(match_data["opponent_id"])

            if not team1 or not team2:
                # todo We need to add this team into DB using specific API request
                # but not at the same time, the task needs to be added to the queue
                continue

            match_data["tournament_id"] = tournament_id

            # поле is_moderated задумывалось как требование ручной корректировки данных
            # в админке т.к. если матч заканчивался по пенальти не было данных из АПИ
            # Решение - купить платный сервис АПИ
            # Пока используем только регулярные чемпионаты поэтому
            # is_moderated можно выставить в True
            match_data["is_moderated"] = True

            matches_to_save.append((team1, team2, match_data))

    return matches_to_save


def request_stats_for_matches(matches):
    endpoint = main_api.get_endpoint("get_goals_stats")

    matches_to_update = {}

    for m in matches:

        payload = main_api.get_payload(
            task="get_goals_stats", match_obj=m, main_api_model=main_api_model
        )

        response = main_api.send_request(endpoint, payload)
        increase_api_requests_count()

        if response["errors"]:
            return None

        goals = api_parser.parse_goals(response)
        goals_stats = api_parser.get_goals_stats(goals)

        if goals_stats:
            matches_to_update[m.id] = goals_stats

    return matches_to_update


def request_teams_by_tournaments(tournaments):

    endpoint = main_api.get_endpoint("get_teams")

    teams_by_country = {}

    for t in tournaments:

        tournament_api_obj = main_api_model.get_tournament_api_obj_by_tournament(t)
        if not tournament_api_obj:
            continue

        tournament_api_id = tournament_api_obj.api_football_id
        tournament_api_season = main_api_model.get_tournament_api_season_by_tournament(
            t
        )

        payload = main_api.get_payload(
            task="get_teams",
            tournament_api_id=tournament_api_id,
            tournament_api_season=tournament_api_season,
        )

        response = main_api.send_request(endpoint, payload)

        increase_api_requests_count()

        if response["errors"]:
            return HttpResponse("Response Errors: please check the logs for details")

        teams = api_parser.parse_teams(response)

        teams_by_country[t.country.id] = teams

    return teams_by_country


def prepare_teams_data_for_saving(teams_by_country):
    teams_to_save, teams_to_add_logo = [], []

    for country_id, teams in teams_by_country.items():
        for team in teams:
            team_id = api_parser.get_team_id(team)
            team_name = api_parser.get_team_name(team)
            team_logo = api_parser.get_team_logo(team)

            api_team_record = main_api_model.get_team_record(team_id)

            if api_team_record:
                team_obj = api_team_record.content_object
                if team_logo and not team_obj.logo:
                    teams_to_add_logo.append((team_obj, team_logo))

            else:
                teams_to_save.append((team_id, team_name, country_id, team_logo))

    return teams_to_save, teams_to_add_logo


def check_api_requests(max_count=0):
    error_message = "We have reached the limit of the API requests"
    api_requests_count = redis_tools.get_api_requests_count(REDIS_CONNECTION)
    if max_count and api_requests_count >= max_count:
        async_error_logging.delay(error_message)
        return HttpResponse(error_message)


def increase_api_requests_count():
    redis_tools.increase_api_requests_count(REDIS_CONNECTION)
