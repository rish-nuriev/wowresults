from django.urls import path, register_converter

from tournaments.converters import DateConverter

from . import views

register_converter(DateConverter, 'date')

urlpatterns = [
    path('get_results/', views.get_results, name='getres'),
    path('get_results/<date:start_date>', views.get_results, name='getres_with_date'),
    path('get_results/<date:start_date>/<int:single_day>/', views.get_results, name='getres_single_day'),
    path('get_teams/', views.get_teams, name='getteams'),
    path('get_goals_stats/', views.get_goals_stats, name='getstats'),
    path('<slug:t_slug>/', views.MatchesByTournament.as_view(), name='tournament'),
    path('<slug:t_slug>/<int:tour>/', views.MatchesByTournament.as_view(), name='tour'),
    path('<slug:t_slug>/<int:tour>/<int:match_id>', views.ShowMatch.as_view(), name='match'),
]
