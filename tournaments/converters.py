from datetime import datetime


class DateConverter:
    regex = r"\d{4}-\d{2}-\d{2}"
    format = "%Y-%m-%d"

    def to_python(self, value):
        return datetime.strptime(value, self.format).date()

    def to_url(self, value):
        return value.strftime(self.format)
