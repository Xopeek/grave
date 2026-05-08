import os
from datetime import timedelta

import django
import discord
from asgiref.sync import sync_to_async
from discord.ext import commands
from django.db.models import Prefetch
from django.utils import timezone
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "grave.settings")
django.setup()

from lineup.models import GameCellAssignment, ScheduleGame

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

REMINDER_MARKER = "[AUTO_2H_REMINDER]"
TABLE_NAMES = (
    "BLUE",
    "PURPLE",
    "RED",
    "GREEN",
    "PINK",
    "YELLOW",
    "ORANGE",
    "CYAN",
)

intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


def _format_role_name(role_icon: str) -> str:
    if not role_icon:
        return "не указана"

    name = role_icon.rsplit(".", 1)[0]
    if name.startswith("T_role_"):
        name = name[len("T_role_"):]
    elif name.startswith("T_"):
        name = name[len("T_"):]

    name = name.replace("_", " ").strip()
    return name or "не указана"


def _format_squad_name(cell_index: int, page_number: int) -> str:
    if cell_index is None or cell_index < 0:
        return "UNKNOWN"

    squad_index = cell_index // 6
    slot_number = (cell_index % 6) + 1
    squad_name = TABLE_NAMES[squad_index] if squad_index < len(TABLE_NAMES) else "UNKNOWN"

    if page_number and page_number != 1:
        return f"{squad_name} стр.{page_number}, слот {slot_number}"
    return f"{squad_name}, слот {slot_number}"


@sync_to_async(thread_sensitive=True)
def _get_upcoming_games():
    now = timezone.now()
    reminder_deadline = now + timedelta(hours=2)
    assignments_qs = (
        GameCellAssignment.objects
        .select_related("participant")
        .order_by("page_number", "cell_index")
    )

    return list(
        ScheduleGame.objects
        .filter(
            game_start_time__isnull=False,
            game_start_time__gt=now,
            game_start_time__lte=reminder_deadline,
        )
        .exclude(tags__icontains="Отмена")
        .prefetch_related(Prefetch("assignments", queryset=assignments_qs))
    )


def _build_reminder_message(game: ScheduleGame) -> str | None:
    assignments = list(game.assignments.all())
    if not assignments:
        return None

    lines = []
    for assignment in assignments:
        participant = assignment.participant
        mention = (
            f"<@{participant.discord_user_id}>"
            if participant and participant.discord_user_id
            else participant.name
        )
        squad_name = _format_squad_name(assignment.cell_index, assignment.page_number)
        role_name = _format_role_name(assignment.role_icon)
        lines.append(f"- {mention} — отряд: {squad_name}, роль: {role_name}")

    start_str = timezone.localtime(game.game_start_time).strftime("%d.%m.%Y %H:%M")
    return (
        f"{REMINDER_MARKER}\n"
        f"@here Напоминание: до начала игры **{game.name}** осталось меньше 2 часов.\n"
        f"Старт: **{start_str}**\n\n"
        f"Расстановка:\n" + "\n".join(lines)
    )


async def _has_reminder_marker(thread: discord.abc.Messageable) -> bool:
    async for message in thread.history(limit=50):
        if message.author.id == bot.user.id and REMINDER_MARKER in (message.content or ""):
            return True
    return False


async def _send_reminders():
    games = await _get_upcoming_games()
    for game in games:
        message = _build_reminder_message(game)
        if not message:
            continue

        try:
            channel = await bot.fetch_channel(game.discord_thread_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            continue

        if not isinstance(channel, discord.Thread):
            continue

        if await _has_reminder_marker(channel):
            continue

        await channel.send(message)


async def run_two_hours_reminder():
    @bot.event
    async def on_ready():
        try:
            await _send_reminders()
        finally:
            await bot.close()

    await bot.start(TOKEN)
