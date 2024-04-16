from django.core.exceptions import ValidationError
from django import forms

from .models import Team


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = '__all__'

    def clean(self):
        cleaned_data = super(TeamForm, self).clean()
        if cleaned_data.get("title") == 'Loko':
            raise ValidationError("Команду нельзя называть Локо!!!")
        return cleaned_data
