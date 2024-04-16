from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import dateformat
from django.utils.text import slugify
from articles.models import Article

from tournaments.models import Match

def translit_to_eng(s: str) -> str:
    d = {'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
         'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i', 'к': 'k',
         'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
         'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch',
         'ш': 'sh', 'щ': 'shch', 'ь': '', 'ы': 'y', 'ъ': '', 'э': 'r', 'ю': 'yu', 'я': 'ya'}

    return "".join(map(lambda x: d[x] if d.get(x, False) else x, s.lower()))


@login_required
def create(request, match_day):
    tournaments_to_process = (
        Match.main_matches.values(
            "tournament__id", "tournament__title", "tournament__season"
        )
        .filter(date=match_day)
        .distinct()
    )

    for tournament in tournaments_to_process:
        matches = Match.main_matches.filter(
            tournament=tournament["tournament__id"], date=match_day
        )
        nice_date = dateformat.format(match_day, settings.DATE_FORMAT)
        title = f'Результаты матчей: {tournament["tournament__title"]} {tournament["tournament__season"]} - {nice_date}'
        text = f'<h2>{nice_date} состоялись следующие матчи:</h2></br><ul>'
        for match in matches:
            text += f'<li>{ match.main_team }-{ match.opponent } : { match.goals_scored } - { match.goals_conceded }</li>'
        text += '</ul>'
        slug = slugify(translit_to_eng(title))

        defaults = {
            'title': title,
            'slug': slug,
            'content': text,
            'tournament_id': tournament['tournament__id'],
            'match_day': match_day
        }

        Article.objects.update_or_create(
            slug = slug,
            defaults = defaults
        )

    return render(request, "articles/create.html", {"tourns": tournaments_to_process})
