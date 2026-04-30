from django.contrib import admin
from django.urls import path, include
from rest_framework import routers

import lineup.views as views


router = routers.DefaultRouter()
router.register('api/game', views.ScheduleGameViewSet)


urlpatterns = [
    path('games/', views.schedule_games_page),
    path('api/assign/', views.GameAssignmentView.as_view()),
    path('', include(router.urls)),
]
