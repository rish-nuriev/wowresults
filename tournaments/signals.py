import logging
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, pre_delete
from django.conf import settings
import tournaments.models as t_models


logger = logging.getLogger("basic_logger")


@receiver(pre_delete, sender=t_models.Match)
def match_pre_delete_handler(sender, instance, **kwargs):
    if instance.at_home:
        try:
            related_match = t_models.Match.objects.get(opposite_match=instance.pk)
            related_match.delete()

            main_api_model = getattr(t_models, settings.MAIN_API_MODEL)

            related_api_model_object = main_api_model.get_api_match_record_by_match_obj(
                instance
            )
            related_api_model_object.delete()

        except t_models.Match.DoesNotExist:
            logger.error("Related match doesn't exist in match_pre_delete_handler")
        except main_api_model.DoesNotExist:
            logger.error("related_api_model_object doesn't exist in match_pre_delete_handler")


@receiver(pre_save, sender=t_models.Match)
def match_pre_save_handler(sender, instance, **kwargs):
    # в данном методе на основании забитых и пропущенных мячей
    # вычисляетс результат а также кол-во полученных очков
    instance.points_received = 0
    if instance.goals_scored is not None and instance.goals_conceded is not None:
        if instance.goals_scored > instance.goals_conceded:
            instance.result = t_models.Match.ResultVals.WIN
            instance.points_received = instance.tournament.points_per_win
        elif instance.goals_scored < instance.goals_conceded:
            instance.result = t_models.Match.ResultVals.LOSE
        else:
            instance.result = t_models.Match.ResultVals.DRAW
            instance.points_received = instance.tournament.points_per_draw
    else:
        instance.result = None


@receiver(post_save, sender=t_models.Match)
def match_post_save_handler(sender, instance, created, **kwargs):
    # в данном методе создаю объект Матча для команды на выезде
    # это необходимо чтобы всегда можно было полуить все матчи для команды
    # как на выезде так и дома.
    # А также сохраняю объект связанной модели АПИ для матча дома
    if instance.at_home:

        main_team = instance.opponent
        results = t_models.Match.ResultVals

        result = None

        if instance.result:
            match instance.result:
                case results.WIN:
                    result = results.LOSE
                case results.LOSE:
                    result = results.WIN
                case _:
                    result = results.DRAW

        points_received = (
            instance.tournament.points_per_win
            if result == results.WIN
            else instance.tournament.points_per_draw if result == results.DRAW else 0
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
        }

        if created:
            main_api_model = getattr(t_models, settings.MAIN_API_MODEL)

            api_model_object = main_api_model()

            api_model_object.api_football_id = instance.temporary_match_id
            api_model_object.content_object = instance
            api_model_object.save()

        else:
            data["pk"] = t_models.Match.objects.get(opposite_match=instance.pk).pk

        for k, v in data.items():
            setattr(instance, k, v)

        instance.save()
