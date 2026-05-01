from django.contrib.sessions.models import Session
from django.db import transaction
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
import re
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from lineup.models import ScheduleGame, GameParticipant, GameCellAssignment
from lineup.serializers import ScheduleGameSerializer


class ScheduleGameViewSet(viewsets.ModelViewSet):
    queryset = ScheduleGame.objects.all()
    http_method_names = ['get', 'patch']
    serializer_class = ScheduleGameSerializer
    permission_classes = [IsAuthenticated]


class GameAssignmentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        game_id = request.data.get('game_id')
        participant_id = request.data.get('participant_id')
        cell_index = request.data.get('cell_index')
        page_number = request.data.get('page_number', 1)
        role_icon = request.data.get('role_icon', '')
        vehicle_icon = request.data.get('vehicle_icon', '')
        vehicle_color = request.data.get('vehicle_color', '#ffffff')

        try:
            page_number = int(page_number)
        except (TypeError, ValueError):
            return Response({'error': 'invalid page_number'}, status=400)

        if page_number not in (1, 2):
            return Response({'error': 'invalid page_number'}, status=400)

        if role_icon is None:
            role_icon = ''
        if not isinstance(role_icon, str):
            return Response({'error': 'invalid role_icon'}, status=400)
        role_icon = role_icon[:120]
        if vehicle_icon is None:
            vehicle_icon = ''
        if not isinstance(vehicle_icon, str):
            return Response({'error': 'invalid vehicle_icon'}, status=400)
        vehicle_icon = vehicle_icon[:120]
        if vehicle_color is None:
            vehicle_color = '#ffffff'
        if not isinstance(vehicle_color, str):
            return Response({'error': 'invalid vehicle_color'}, status=400)
        vehicle_color = vehicle_color.strip().lower()
        if not re.fullmatch(r'^#[0-9a-f]{6}$', vehicle_color):
            return Response({'error': 'invalid vehicle_color'}, status=400)

        if not all([game_id, participant_id]):
            return Response({'error': 'invalid data'}, status=400)

        try:
            game = ScheduleGame.objects.get(id=game_id)
            participant = GameParticipant.objects.get(id=participant_id, game=game)
        except ScheduleGame.DoesNotExist:
            return Response({'error': 'game not found'}, status=404)
        except GameParticipant.DoesNotExist:
            return Response({'error': 'participant not found'}, status=404)

        with transaction.atomic():
            # удаляем старое назначение игрока
            GameCellAssignment.objects.filter(
                game=game,
                participant=participant,
                page_number=page_number
            ).delete()

            if cell_index is not None:
                # удаляем игрока, который уже сидит в этой ячейке
                GameCellAssignment.objects.filter(
                    game=game,
                    cell_index=cell_index,
                    page_number=page_number
                ).delete()

                GameCellAssignment.objects.create(
                    game=game,
                    participant=participant,
                    cell_index=cell_index,
                    page_number=page_number,
                    role_icon=role_icon,
                    vehicle_icon=vehicle_icon,
                    vehicle_color=vehicle_color
                )

        return Response({'status': 'ok'})


@ensure_csrf_cookie
def schedule_games_page(request):
    context = {}

    if request.user.is_authenticated:
        display_name = request.user.first_name or request.user.get_username()
        avatar_url = ''

        discord_account = getattr(request.user, 'discord_account', None)
        if discord_account and discord_account.discord_avatar:
            avatar_url = (
                f"https://cdn.discordapp.com/avatars/"
                f"{discord_account.discord_id}/{discord_account.discord_avatar}.png?size=128"
            )

        context.update({
            'header_display_name': display_name,
            'header_avatar_url': avatar_url,
        })

    return render(request, 'lineup.html', context)
