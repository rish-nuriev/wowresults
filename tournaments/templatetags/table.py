from django import template
from django.db import connection
from django.db.models import CharField, Sum, Count, IntegerField
from django.db.models.functions import Cast
from django.contrib.postgres.aggregates.general import StringAgg
from django.db.models import Aggregate

from tournaments.models import Match


class Concat(Aggregate):
    function = "GROUP_CONCAT"
    template = "%(function)s(%(distinct)s%(expressions)s)"

    def __init__(self, expression, distinct=False, **extra):
        super(Concat, self).__init__(
            expression,
            distinct="DISTINCT " if distinct else "",
            output_field=CharField(),
            **extra
        )


register = template.Library()


@register.inclusion_tag("tournaments/table.html")
def show_table(tournament, tour=0, date=None):
    """
    Тег отрисовывает таблицу с результатами.
    По наименованию команды группируются все матчи.
    Суммируется кол-во матчей, набранные очки,
    забитые и пропущенные мячи, их разница.
    Запрос сортируется по кол-ву очков, потом разнице мячей,
    потом по кол-ву забитых мячей.
    Строка результатов аггрегируется в виде 'WDLWWL'
    в соответствии со статусами Match.ResultVals
    Затем в темплейте высчитывается кол-во побед, ничей и поражений.
    Функция аггрегации результатов выбирается в зависимости 
    от движка базы данных.
    """
    if connection.vendor == "postgresql":
        aggregation = StringAgg
    else:
        aggregation = Concat
    q = (
        Match.objects.select_related("Tournament")
        .values("main_team__title")
        .filter(tournament=tournament, status=Match.Statuses.FULL_TIME)
    )
    if tour:
        q = q.filter(tour__lte=tour)
    if date:
        q = q.filter(date__lte=date)
    matches = (
        q.annotate(
            results=aggregation("result", delimiter=""),
            cnt=Count("id"),
            points=Sum("points_received"),
            goals_scored=Sum("goals_scored"),
            goals_conceded=Sum("goals_conceded"),
        )
        .annotate(
            g_diff=(
                Cast("goals_scored", IntegerField())
                - Cast("goals_conceded", IntegerField())
            )
        )
        .order_by("-points", "-g_diff", "-goals_scored")
    )

    events = tournament.events.all()

    events_by_team = {}
    for event in events:
        if event.team:
            events_by_team[event.team.title] = {
                "operation": event.operation,
                "value": event.value,
            }

    return {
        "matches": matches,
        "events_by_team": events_by_team,
        "rtypes": {
            "Win": Match.ResultVals.WIN,
            "Draw": Match.ResultVals.DRAW,
            "Lose": Match.ResultVals.LOSE,
        },
    }
