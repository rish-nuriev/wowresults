from django import template
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
def show_table(t_slug, rtypes="WDL", tour=0):
    q = Match.objects.values("main_team__title").filter(
        tournament__slug=t_slug, status=Match.Statuses.FULL_TIME
    )
    if tour:
        q = q.filter(tour__lte=tour)
    matches = (
        q.annotate(
            results=Concat("result", delimiter=""),
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
    return {
        "matches": matches,
        "rtypes": {
            "Win": rtypes.WIN,
            "Draw": rtypes.DRAW,
            "Lose": rtypes.LOSE,
        },
    }
