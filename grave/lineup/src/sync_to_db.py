import os
import re
from datetime import datetime

import django
from asgiref.sync import sync_to_async
from django.db import transaction

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "grave.settings")
django.setup()

from lineup.models import ScheduleGame, GameParticipant


@sync_to_async(thread_sensitive=True)
def save_game_to_db(thread_id, name, archived, tags, created_at, game_start_time=None):
    defaults = {
        "name": name,
        "archived": archived,
        "tags": tags,
        "created_at": created_at,
    }
    if game_start_time is not None:
        if isinstance(game_start_time, datetime):
            defaults["game_start_time"] = game_start_time.isoformat(sep=" ")
        else:
            defaults["game_start_time"] = str(game_start_time)

    # Avoid reading existing row first (update_or_create/get_or_create),
    # because legacy SQLite values may fail during DateTime conversion.
    updated_rows = ScheduleGame.objects.filter(discord_thread_id=thread_id).update(**defaults)
    if updated_rows:
        return ScheduleGame.objects.filter(discord_thread_id=thread_id).first(), False

    return ScheduleGame.objects.create(
        discord_thread_id=thread_id,
        **defaults,
    ), True


def parse_embed_field_value(value: str) -> list[str]:
    lines = []
    for line in value.splitlines():
        line = line.strip()
        if not line:
            continue
        line = line.replace(">>>", "").strip()
        line = re.sub(r"<:[^:]+:\d+>", "", line)
        if line:
            lines.append(line)

    return lines


def parse_embed(embed):
    statuses = {
        "Accepted": [],
        "Tentative": [],
        "Waitlist": [],
    }

    for field in embed.fields:
        for status in statuses:
            if status in field.name:
                statuses[status] = parse_embed_field_value(field.value)

    return statuses


@sync_to_async(thread_sensitive=True)
def save_participants(game_id, statuses, member_map):
    game = ScheduleGame.objects.get(discord_thread_id=game_id)

    def resolve(name):
        member = member_map.get(name.lower())
        return member.id if member else None

    # новые данные приводим к плоскому виду
    new_data = {}
    for status, users in statuses.items():
        status_key = status.lower()
        for name in users:
            new_data[name] = {
                "status": status_key,
                "discord_user_id": resolve(name),
            }

    with transaction.atomic():
        existing = {
            p.name: p for p in game.participants.all()
        }

        # DELETE лишних
        for name in set(existing) - set(new_data):
            existing[name].delete()

        to_create = []
        to_update = []

        # CREATE / UPDATE
        for name, data in new_data.items():
            if name in existing:
                p = existing[name]
                changed = False

                if p.status != data["status"]:
                    p.status = data["status"]
                    changed = True

                if p.discord_user_id != data["discord_user_id"]:
                    p.discord_user_id = data["discord_user_id"]
                    changed = True

                if changed:
                    to_update.append(p)

            else:
                to_create.append(GameParticipant(
                    game=game,
                    name=name,
                    status=data["status"],
                    discord_user_id=data["discord_user_id"],
                ))

        if to_create:
            GameParticipant.objects.bulk_create(to_create)

        if to_update:
            GameParticipant.objects.bulk_update(
                to_update,
                ["status", "discord_user_id"]
            )
