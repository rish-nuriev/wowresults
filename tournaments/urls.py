from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name="home"),
    path('tournament/<slug:t_slug>/', views.MatchesByTournament.as_view(), name='tournament'),
    path('tournament/<slug:t_slug>/<int:tour>/', views.MatchesByTournament.as_view(), name='tour'),
    path('tournament/<slug:t_slug>/<int:tour>/<int:match_id>', views.ShowMatch.as_view(), name='match'),
    path('get_results/', views.get_results, name='getres'),
    path('get_teams/', views.get_teams, name='getteams'),
    path('get_goals_stats/', views.get_goals_stats, name='getstats'),
]
