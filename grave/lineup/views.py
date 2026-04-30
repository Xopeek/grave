from django.contrib.sessions.models import Session
from django.db import transaction
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from lineup.models import ScheduleGame, GameParticipant, GameCellAssignment
from lineup.serializers import ScheduleGameSerializer


class ScheduleGameViewSet(viewsets.ModelViewSet):
    queryset = ScheduleGame.objects.all()
    http_method_names = ['get', 'patch']
    serializer_class = ScheduleGameSerializer


class GameAssignmentView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        game_id = request.data.get('game_id')
        participant_id = request.data.get('participant_id')
        cell_index = request.data.get('cell_index')

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
                participant=participant
            ).delete()

            if cell_index is not None:
                # удаляем игрока, который уже сидит в этой ячейке
                GameCellAssignment.objects.filter(
                    game=game,
                    cell_index=cell_index
                ).delete()

                GameCellAssignment.objects.create(
                    game=game,
                    participant=participant,
                    cell_index=cell_index
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
    print("Host:", request.get_host())
    print("Scheme:", request.scheme)
    session_cookie = request.COOKIES.get('sessionid')
    if session_cookie:
        exists = Session.objects.filter(session_key=session_cookie).exists()
        print(f"Session from cookie '{session_cookie}' exists in DB: {exists}")
    print("USER:", request.user)
    print("AUTH:", request.user.is_authenticated)
    print("SESSION:", request.session.session_key)

    print("Cookies:", request.COOKIES)
    print("Session key from request:", request.session.session_key)

    return render(request, 'lineup.html', context)
