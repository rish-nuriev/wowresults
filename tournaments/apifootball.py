from django.conf import settings
from django.core.mail import send_mail
import requests


class ApiFootball:

    API_URL = f"https://{settings.APIFOOTBALL_HOST}/"

    def __init__(self):
        self.headers = {
            "x-rapidapi-key": settings.APIFOOTBALL_KEY,
            "x-rapidapi-host": settings.APIFOOTBALL_HOST,
        }


    def send_request(self, endpoint:str, payload:dict):

        url = self.API_URL + endpoint

        response = {}

        error_subject = "Ошибка при запросе к АПИ Футбол"

        try:
            response = requests.request(
                "GET", url, headers=self.headers, params=payload, timeout=10
            ).json()
        except Exception as err:
            error_message = f"ОШИБКА: {err}"
            send_mail(error_subject, error_message, settings.ADMIN_EMAIL, (settings.WORKING_EMAIL,))

        if response["errors"]:
            error_message = f'Response Errors: {response["errors"]}'
            send_mail(error_subject, error_message, settings.ADMIN_EMAIL, (settings.WORKING_EMAIL,))

        if not response:
            response["errors"] = "Something went wrong, please check the logs for details"

        return response
