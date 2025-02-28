import os
from django.conf import settings
from django.utils import dateformat
from articles.helpers import gen_match_text

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
        raise ArticleGenerationError(f'Couldn\'t get the template - {ex}') from ex

    text, matches_list = "", ""
    for match in matches:
        text += gen_match_text(
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
        tags.append(f'{tournament["tournament__title"]} {tournament["tournament__season"]} {tour} тур')

    return tags
