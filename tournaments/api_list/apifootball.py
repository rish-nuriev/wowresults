import logging
from django.conf import settings

import requests
from tournaments.api_list.api_interface import ApiInterface

logger = logging.getLogger("basic_logger")


class ApiFootballException(Exception):
    pass


class ApiFootball(ApiInterface):
    """
    Класс для работы с АПИ от api-football.com.
    Бесплатная версия позволяет посылать лишь 100 запросов в сутки.
    Поэтому значение MAX_REQUESTS_COUNT=100.
    В соответствии с интерфейсом ApiInterface, класс реализует 4 метода:
    get_max_requests_count, get_endpoint, get_payload, send_request
    """

    API_URL = f"https://{settings.APIFOOTBALL_HOST}/"
    MAX_REQUESTS_COUNT = 100
    DATE_FORMAT = "%Y-%m-%d"

    def __init__(self):
        self.headers = {
            "x-rapidapi-key": settings.APIFOOTBALL_KEY,
            "x-rapidapi-host": settings.APIFOOTBALL_HOST,
        }

    def send_request(self, endpoint: str, payload: dict):
        """
        Отправка запроса к АПИ.
        Цель получить ответ в JSON формате.
        В дальнейшем специальный класс ApiFootballParser
        должен обработать запрос и получить необходимые данные.
        Возникшие ошибки логируются (админу отправляется Email-сообщение)
        """
        url = self.API_URL + endpoint

        response = {}

        try:
            response = requests.request(
                "GET", url, headers=self.headers, params=payload, timeout=10
            ).json()
        except ApiFootballException as err:
            error_message = f"ОШИБКА: {err}"
            response["errors"] = error_message

        if not response:
            response["errors"] = (
                "Something went wrong, please check the logs for details"
            )

        if response["errors"]:
            error_message = f'Ошибка при запросе к АПИ Футбол - Response Errors: {response["errors"]}'
            logger.error(error_message)

        return response

    def get_endpoint(self, task: str) -> str:
        match task:
            case "results_by_tournament":
                return "fixtures"
            case "get_teams":
                return "teams"
            case "get_goals_stats":
                return "fixtures/events"
        return "fixtures"

    def get_max_requests_count(self) -> int:
        return self.MAX_REQUESTS_COUNT

    def get_payload(self, *args, **kwargs) -> dict:
        if "task" in kwargs:
            match kwargs["task"]:
                case "results_by_tournament":
                    return {
                        "league": kwargs["tournament_api_id"],
                        "season": kwargs["tournament_api_season"],
                        "date": kwargs["date"],
                    }
                case "get_teams":
                    return {
                        "league": kwargs["tournament_api_id"],
                        "season": kwargs["tournament_api_season"],
                    }
                case "get_goals_stats":
                    m = kwargs["match_obj"]
                    match_api_id = 0
                    if not match_api_id:
                        main_api_model = kwargs["main_api_model"]
                        api_match_record = (
                            main_api_model.__class__.get_api_match_record_by_match_obj(
                                m
                            )
                        )
                        if api_match_record:
                            match_api_id = api_match_record.api_football_id

                    return {
                        "fixture": match_api_id,
                    }
        return {}
