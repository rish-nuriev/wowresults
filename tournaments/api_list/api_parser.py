import logging


logger = logging.getLogger('basic_logger')

class ApiParsersContainer:

    CLASSES = {
        "ApiFootball": "ApiFootballParser",
    }

    def __init__(self, api) -> None:
        self.__api = api

    def get_api_parser(self):
        if self.__api.__class__.__name__ in self.CLASSES:
            return globals()[self.CLASSES[self.__api.__class__.__name__]]()


class ApiParserError(Exception):
    pass


class ApiFootballParser:

    @staticmethod
    def get_parsed_data_or_raise_error(data, error="Parsing Error"):
        try:
            return data
        except KeyError as key_error:
            logger.error(error)
            raise ApiParserError(
                f"Response is missing critical data - {error}"
            ) from key_error

    def parse_matches(self, response):
        return self.get_parsed_data_or_raise_error(
            response["response"], error="parse_matches Response error"
        )

    def parse_teams(self, response):
        return self.get_parsed_data_or_raise_error(
            response["response"], error="parse_teams Response error"
        )

    def parse_goals(self, response):
        return self.get_parsed_data_or_raise_error(
            response["response"], error="parse_goals Response error"
        )

    def get_match_id(self, match):
        return self.get_parsed_data_or_raise_error(
            match["fixture"]["id"], "get_match_id error"
        )

    def get_match_date(self, match):
        return self.get_parsed_data_or_raise_error(
            match["fixture"]["date"], "get_date_from_match Match error"
        )

    def get_main_team_id(self, match):
        return self.get_parsed_data_or_raise_error(
            match["teams"]["home"]["id"],
            "get_main_team_id_from_match Match error",
        )

    def get_opponent_id(self, match):
        return self.get_parsed_data_or_raise_error(
            match["teams"]["away"]["id"],
            "get_opponent_id_from_match Match error",
        )

    def get_tour(self, match):
        try:
            return int(match["league"]["round"].split(" - ")[1])
        except KeyError:
            print("The match is out of regular")
        except ValueError:
            print("Wrong value was given for Tour")

    def get_status(self, match):
        return self.get_parsed_data_or_raise_error(
            match["fixture"]["status"]["short"],
            "get_status Match error",
        )

    def get_goals_scored(self, match):
        return self.get_parsed_data_or_raise_error(
            match["goals"]["home"],
            "get_goals_scored Match error",
        )

    def get_goals_conceded(self, match):
        return self.get_parsed_data_or_raise_error(
            match["goals"]["away"],
            "get_goals_conceded Match error",
        )

    def get_score(self, match):
        return self.get_parsed_data_or_raise_error(
            match["score"],
            "get_score Match error",
        )

    def get_team_id(self, team):
        return self.get_parsed_data_or_raise_error(
            team["team"]["id"],
            "get_team_id Team error",
        )

    def get_team_name(self, team):
        return self.get_parsed_data_or_raise_error(
            team["team"]["name"],
            "get_team_name Team error",
        )

    def get_team_logo(self, team):
        return self.get_parsed_data_or_raise_error(
            team["team"]["logo"],
            "get_team_logo Team error",
        )

    def get_goals_stats(self, goals):
        goals_stats = {}
        for event in goals:
            if event["type"] == "Goal":
                minute = event["time"]["elapsed"]
                if event["time"]["extra"]:
                    minute += event["time"]["extra"]
                goals_stats[minute] = {
                    "team": event["team"]["id"],
                    "player": event["player"]["name"],
                    "type": event["detail"],
                }
        return goals_stats
