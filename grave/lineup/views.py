from django.shortcuts import render
from rest_framework import viewsets

from lineup.models import ScheduleGame
from lineup.serializers import ScheduleGameSerializer


class ScheduleGameViewSet(viewsets.ModelViewSet):
    queryset = ScheduleGame.objects.all()
    http_method_names = ['get']
    serializer_class = ScheduleGameSerializer


def schedule_games_page(request):
    return render(request, 'lineup.html')
