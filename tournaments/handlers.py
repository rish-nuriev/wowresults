from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, pre_delete
from tournaments.models import Match


@receiver(pre_delete, sender=Match)
def match_pre_delete_handler(sender, instance, **kwargs):
    if instance.at_home:
        try:
            related_match = Match.objects.get(opposite_match=instance.pk)
            related_match.delete()
        except Match.DoesNotExist:
            print("Related match doesn't exist")  # TODO replace with proper logging


@receiver(pre_save, sender=Match)
def match_pre_save_handler(sender, instance, **kwargs):
    instance.points_received = 0
    if instance.goals_scored is not None and instance.goals_conceded is not None:
        if instance.goals_scored > instance.goals_conceded:
            instance.result = Match.ResultVals.WIN
            instance.points_received = instance.tournament.points_per_win
        elif instance.goals_scored < instance.goals_conceded:
            instance.result = Match.ResultVals.LOSE
        else:
            instance.result = Match.ResultVals.DRAW
            instance.points_received = instance.tournament.points_per_draw
    else:
        instance.result = None


@receiver(post_save, sender=Match)
def match_post_save_handler(sender, instance, created, **kwargs):
    if instance.at_home:
        main_team = instance.opponent
        results = Match.ResultVals

        if instance.result:
            match instance.result:
                case results.WIN:
                    result = results.LOSE
                case results.LOSE:
                    result = results.WIN
                case _:
                    result = results.DRAW
        else:
            result = None

        points_received = (
            instance.tournament.points_per_win
            if result == results.WIN
            else instance.tournament.points_per_draw
            if result == results.DRAW
            else 0
        )

        data = {
            "pk": None,
            "at_home": False,
            "main_team": main_team,
            "opponent": instance.main_team,
            "result": result,
            "points_received": points_received,
            "goals_conceded": instance.goals_scored,
            "goals_scored": instance.goals_conceded,
            "opposite_match": instance.pk,
            "id_api_football": 0,
        }

        if not created:
            data["pk"] = Match.objects.get(opposite_match=instance.pk).pk

        for k, v in data.items():
            setattr(instance, k, v)

        instance.save()
