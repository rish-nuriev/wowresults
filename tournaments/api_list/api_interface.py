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
        raise NotImplementedError("The API should have send_request method")

    def get_endpoint(self, task: str) -> str:
        raise NotImplementedError("The API should have get_endpoint method")

    def get_payload(self, *args, **kwargs) -> dict:
        raise NotImplementedError("The API should have get_payload method")

    def get_max_requests_count(self) -> int:
        raise NotImplementedError("The API should have get_max_requests_count method")
