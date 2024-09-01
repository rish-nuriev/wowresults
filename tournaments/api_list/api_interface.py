class ApiInterface:
    """ We might be using different sources of football results.
        Each new implementation should realize this Interface
        Also specific Model should be created to create associations with the database
        Currenlty we have ApiFootballID model
    """
    def send_request(self, endpoint: str, payload: dict):
        raise NotImplementedError("The API should have send_request method")

    def get_endpoint(self, task: str):
        raise NotImplementedError("The API should have get_endpoint method")

    def get_payload(self, *args, **kwargs) -> dict:
        raise NotImplementedError("The API should have get_payload method")

    def get_max_requests_count(self) -> int:
        raise NotImplementedError("The API should have get_max_requests_count method")
