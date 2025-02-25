from django import forms
from .models import Comment


class SearchForm(forms.Form):
    query = forms.CharField()


class CommentForm(forms.ModelForm):

    body = forms.CharField(
        label="", widget=forms.Textarea(attrs={"class": "form-control"})
    )

    class Meta:
        model = Comment
        fields = ["body"]
