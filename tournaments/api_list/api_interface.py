class ApiInterface:
    """ 
        Проект потенциально может использовать разные АПИ.
        На данный момент используется api-football.com.
        В случае использования другого АПИ нужен соответствующий класс.
        Этот класс должен реализовывать данный интерфейс.
        Кроме этого у другого АПИ будут свои ID сущностей.
        Поэтому также требуется создание соответствующей модели.
        На данный момент это ApiFootballID.
    """
    def send_request(self, endpoint: str, payload: dict):
        """
            Метод отправки запроса к АПИ на конкретный адрес (endpoint).
            Запрос сопровождается данными (payload).
        """
        raise NotImplementedError("The API should have send_request method")

    def get_endpoint(self, task: str) -> str:
        """
        Метод получения конкретного URL для конкретных данных.
        Приложению требуются самые обычные для футбольного АПИ данные.
        Принимает параметр task принимающий следующие значения:
        - results_by_tournament: Ожидаем endpoint для получения 
          результатов матчей определенного турнира
        - get_teams: Ожидаем endpoint для получения данных о командах
        - get_goals_stats: Ожидаем endpoint для получения 
          статистики определенного матча
        """
        raise NotImplementedError("The API should have get_endpoint method")

    def get_payload(self, task: str, *args, **kwargs) -> dict:
        """
        Метод получения данных для запросов.
        Данные определяются на основании переданной таски (task).
        Ожидаем уже конкретный словарь с данными для отправки запроса.
        Параметр task принимающий следующие значения:
        - results_by_tournament: для получения результатов матчей. 
          Вместе с данным task передаются также tournament_api_id, 
          tournament_api_season, date (этого должно быть достаточно 
          для получения результатов).
        - get_teams: для получения даннх о командах. 
          Вместе с данным task передаются также tournament_api_id,
          tournament_api_season.
        - get_goals_stats: для получения статистики матча.
          Вместе с данным task передаются также match_obj, main_api_model.
        """
        raise NotImplementedError("The API should have get_payload method")

    def get_max_requests_count(self) -> int:
        """
        Метод возвращает максимальное суточное количество запросов к АПИ
        """
        raise NotImplementedError("The API should have get_max_requests_count method")
