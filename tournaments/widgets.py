from datetime import date
from django import forms

class CustomDatePickerInput(forms.DateInput):
    template_name = "tournaments/widgets/custom_datepicker.html"

    class Media:
        css = {
            "all": (
                "css/datepicker.min.css",
            )
        }
        js = (
            "js/jquery-3.4.1.min.js",
            "js/datepicker.min.js",
            "js/i18n/datepicker.ru-RU.min.js",
        )


class CustomDatePickerWidgetOld(forms.DateInput):
    DATE_INPUT_WIDGET_REQUIRED_FORMAT = "%Y-%m-%d"

    def __init__(self, attrs=None, format=DATE_INPUT_WIDGET_REQUIRED_FORMAT):
        if not attrs:
            attrs = {}
        attrs.update(
            {
                "class": "form-control",
                "type": "date",
            }
        )
        self.format = format
        super().__init__(attrs, format=self.format)


class PastCustomDatePickerWidget(CustomDatePickerWidgetOld):
    def __init__(self, attrs=None, format=None):
        if not attrs:
            attrs = {}        
        attrs.update({'max': date.today()})
        super().__init__(attrs, format=format)
