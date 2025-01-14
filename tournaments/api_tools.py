import logging
from django.conf import settings
from django.http import HttpResponse
from tournaments.api_list.api_parsers import ApiParserError, ApiParsersContainer
from tournaments import models, utils
import tournaments.api_list.api_classes as api_source

main_api = getattr(api_source, settings.MAIN_API)()
main_api_model = getattr(models, settings.MAIN_API_MODEL)()
api_parsers_container = ApiParsersContainer(main_api)
api_parser = api_parsers_container.get_api_parser()
logger = logging.getLogger("basic_logger")


def get_max_requests_count():
    return main_api.get_max_requests_count()


def request_tournaments_matches_by_date(tournaments, date) -> dict:

    endpoint = main_api.get_endpoint("results_by_tournament")

    matches = {}

    for t in tournaments:

        date = date.strftime(main_api.DATE_FORMAT)

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

        utils.increase_api_requests_count()

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
