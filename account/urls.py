from django.urls import include, path
from account import views

urlpatterns = [
    path("", include('django.contrib.auth.urls')),
    path("", views.dashboard, name="dashboard"),
]
