from django.apps import AppConfig


class TournamentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tournaments"
    verbose_name = "Турниры"

    def ready(self):
        import tournaments.signals
