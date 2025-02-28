import os
import random
from django.conf import settings
from django.utils import dateformat
from tournaments.models import Match

WIN_WORDS = (
    "победил",
    "одолел",
    "переиграл",
    "справился c",
    "разобрался с",
    "сломил сопротивление",
    "превзошел",
    "сразил",
    "осилил",
    "поборол",
    "обыграл",
)

LOSE_WORDS = (
    "проиграл",
    "уступил",
    "потерпел поражение от",
)

SUPER_WIN_WORDS = (
    "разгромил",
    "разнес",
    "уничтожил",
    "с легкостью разобрался с",
    "разбил",
    "разорвал",
    "смял оборону",
    "сокрушил",
    "раскатал",
)

SUPER_LOSE_WORDS = (
    "был разгромлен",
    "был уничтожен",
    "был унижен",
)

DRAW_WORDS = (
    "сыграли вничью",
    "не выявили победителя",
    "разошлись миром",
)


def generate_match_text(team1, team2, result, goals1, goals2):
    if result == Match.ResultVals.WIN:
        if goals1 - goals2 > 2:
            text = f"ФК {team1} {SUPER_WIN_WORDS[random.randint(0, len(SUPER_WIN_WORDS)-1)]} ФК {team2}. "
        else:
            text = f"ФК {team1} {WIN_WORDS[random.randint(0, len(WIN_WORDS)-1)]} ФК {team2}. "
    elif result == Match.ResultVals.LOSE:
        if goals2 - goals1 > 2:
            text = f"ФК {team1} {SUPER_LOSE_WORDS[random.randint(0, len(SUPER_LOSE_WORDS)-1)]} ФК {team2}. "
        else:
            text = f"ФК {team1} {LOSE_WORDS[random.randint(0, len(LOSE_WORDS)-1)]} ФК {team2}. "
    else:
        text = f"ФК {team1} и ФК {team2} {DRAW_WORDS[random.randint(0, len(DRAW_WORDS)-1)]}. "
    return text


class ArticleGenerationError(Exception):
    pass


def get_nice_formatted_date(match_day):
    return dateformat.format(match_day, settings.DATE_FORMAT)


def generate_title(nice_date, tournament):
    return f'Результаты матчей: {tournament["tournament__title"]} {tournament["tournament__season"]} - {nice_date}'


def generate_content_from_template(template_path, nice_date, matches):
    # Построение абсолютного пути к шаблону
    abs_template_path = os.path.join(os.path.dirname(__file__), template_path)
    try:
        with open(abs_template_path, "r", encoding="utf-8") as file:
            template = file.read()
    except FileNotFoundError as ex:
        raise ArticleGenerationError(f"Couldn't get the template - {ex}") from ex

    text, matches_list = "", ""
    for match in matches:
        text += generate_match_text(
            match.main_team,
            match.opponent,
            match.result,
            match.goals_scored,
            match.goals_conceded,
        )
        matches_list += f"<li><a href='{ match.get_absolute_url() }'>{ match.main_team }-{ match.opponent } : { match.goals_scored } - { match.goals_conceded }</a></li>"

    return template.format(nice_date=nice_date, text=text, matches_list=matches_list)


def generate_article_tags(nice_date, matches, tournament):
    tags = []

    for match in matches:
        tags.extend([match.main_team.title, match.opponent.title])

    tags.extend(
        [
            tournament["tournament__title"],
            f"матчи {nice_date}",
        ]
    )

    # Получаем тур из первого матча
    tour = matches[0].tour if matches else None
    if tour:
        tags.append(
            f'{tournament["tournament__title"]} {tournament["tournament__season"]} {tour} тур'
        )

    return tags
