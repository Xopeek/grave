import asyncio
import os
from datetime import timedelta
from io import BytesIO
from pathlib import Path

import django
import discord
from asgiref.sync import sync_to_async
from discord.ext import commands
from django.conf import settings
from django.db.models import Prefetch
from django.utils import timezone
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "grave.settings")
django.setup()

from lineup.models import GameCellAssignment, ScheduleGame

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
STATIC_ROOT = Path(settings.BASE_DIR) / "static"
ICON_DIR = STATIC_ROOT / "icons"
VEHICLE_DIR = STATIC_ROOT / "vehicle"

REMINDER_MARKER = "[AUTO_2H_REMINDER]"
ROLE_PING_NAMES = (
    "гастат",
    "принцип",
    "триарий",
    "трибун ангустиклавии",
    "Mercennarii",
    "Легат Легиона",
)
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
TABLE_COLORS = (
    "#2563eb",
    "#7c3aed",
    "#dc2626",
    "#16a34a",
    "#db2777",
    "#ca8a04",
    "#ea580c",
    "#0891b2",
)
CARD_COLORS = {
    "bg": "#0b1220",
    "card": "#111827",
    "border": "#2a3447",
    "text": "#e5e7eb",
    "muted": "#9ca3af",
    "chip_bg": "#1f2937",
    "chip_border": "#334155",
    "slot_bg": "#0f172a",
    "slot_border": "#475569",
    "row_line": "#273449",
}

intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True

_ICON_CACHE: dict[str, Image.Image] = {}


def _load_font(size: int) -> ImageFont.ImageFont:
    for font_name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _load_icon(path: Path, size: tuple[int, int]) -> Image.Image | None:
    cache_key = f"{path}:{size[0]}x{size[1]}"
    cached = _ICON_CACHE.get(cache_key)
    if cached is not None:
        return cached.copy()
    if not path.exists():
        return None
    try:
        icon = Image.open(path).convert("RGBA")
    except OSError:
        return None
    icon.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    x = (size[0] - icon.width) // 2
    y = (size[1] - icon.height) // 2
    canvas.paste(icon, (x, y), icon)
    _ICON_CACHE[cache_key] = canvas
    return canvas.copy()


def _truncate(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    if not text:
        return ""
    if draw.textlength(text, font=font) <= max_width:
        return text

    ellipsis = "..."
    current = text
    while current and draw.textlength(f"{current}{ellipsis}", font=font) > max_width:
        current = current[:-1]
    return f"{current}{ellipsis}" if current else ellipsis


def _normalize_vehicle_color(color: str) -> str:
    if not isinstance(color, str):
        return "#ffffff"
    value = color.strip().lower()
    if len(value) == 7 and value.startswith("#"):
        valid_chars = "0123456789abcdef"
        if all(ch in valid_chars for ch in value[1:]):
            return value
    return "#ffffff"


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


def _build_page_lineup_image(
    game: ScheduleGame,
    page_number: int,
    page_data: dict[int, GameCellAssignment],
) -> bytes | None:
    if not page_data:
        return None

    width = 2000
    title_font = _load_font(34)
    subtitle_font = _load_font(24)
    squad_font = _load_font(22)
    text_font = _load_font(18)
    mini_font = _load_font(15)

    header_x = 40
    header_top = 28
    start_str = timezone.localtime(game.game_start_time).strftime("%d.%m.%Y %H:%M")

    card_x, card_y = 40, 154
    card_w = width - 80

    grid_gap = 20
    grid_side_padding = 24
    row_gap = 18
    table_w = (card_w - (grid_side_padding * 2) - (grid_gap * 2)) // 3
    table_h = 320
    card_h = 24 + (table_h * 3) + (row_gap * 2) + 24
    height = card_y + card_h + 30
    image = Image.new("RGB", (width, height), CARD_COLORS["bg"])
    draw = ImageDraw.Draw(image)
    draw.text((header_x, header_top), f"Расстановка: {game.name}", fill=CARD_COLORS["text"], font=title_font)
    draw.text((header_x, header_top + 50), f"Старт: {start_str}", fill=CARD_COLORS["muted"], font=subtitle_font)
    draw.text((header_x, header_top + 86), f"Страница {page_number}", fill=CARD_COLORS["text"], font=subtitle_font)

    draw.rounded_rectangle(
        (card_x, card_y, card_x + card_w, card_y + card_h),
        radius=18,
        fill=CARD_COLORS["card"],
        outline=CARD_COLORS["border"],
        width=2,
    )

    row_y_positions = (
        card_y + 24,
        card_y + 24 + table_h + row_gap,
        card_y + 24 + (table_h + row_gap) * 2,
    )
    row_layout = (
        (0, 1, 2),
        (3, 4, 5),
        (6, 7),
    )

    for row_index, row_squads in enumerate(row_layout):
        table_count = len(row_squads)
        row_content_w = table_count * table_w + (table_count - 1) * grid_gap
        start_x = card_x + (card_w - row_content_w) // 2
        table_y = row_y_positions[row_index]

        for col_index, squad_idx in enumerate(row_squads):
            squad_name = TABLE_NAMES[squad_idx]
            table_x = start_x + col_index * (table_w + grid_gap)

            draw.rounded_rectangle(
                (table_x, table_y, table_x + table_w, table_y + table_h),
                radius=12,
                fill=CARD_COLORS["card"],
                outline=CARD_COLORS["border"],
                width=2,
            )
            draw.rounded_rectangle(
                (table_x, table_y, table_x + table_w, table_y + 34),
                radius=12,
                fill=TABLE_COLORS[squad_idx],
                outline=TABLE_COLORS[squad_idx],
            )
            draw.text((table_x + 10, table_y + 9), squad_name, fill="#ffffff", font=squad_font)

            row_h = (table_h - 44) // 6
            for slot in range(6):
                cell_index = squad_idx * 6 + slot
                row_y = table_y + 38 + slot * row_h

                if slot > 0:
                    draw.line(
                        (table_x + 1, row_y, table_x + table_w - 1, row_y),
                        fill=CARD_COLORS["row_line"],
                        width=1,
                    )

                draw.text((table_x + 8, row_y + 8), str(slot + 1), fill=CARD_COLORS["muted"], font=text_font)
                assignment = page_data.get(cell_index)
                if not assignment:
                    continue

                participant = assignment.participant
                player_name = participant.name if participant else "Unknown"
                role_icon_name = assignment.role_icon or ""
                vehicle_icon_name = assignment.vehicle_icon or ""
                vehicle_color = _normalize_vehicle_color(assignment.vehicle_color or "#ffffff")
                if vehicle_color == "#ffffff":
                    vehicle_color = CARD_COLORS["slot_border"]

                chip_x = table_x + 30
                chip_y = row_y + 5
                chip_w = table_w - 36
                chip_h = row_h - 10
                draw.rounded_rectangle(
                    (chip_x, chip_y, chip_x + chip_w, chip_y + chip_h),
                    radius=10,
                    fill=CARD_COLORS["chip_bg"],
                    outline=CARD_COLORS["chip_border"],
                    width=1,
                )

                icon_size = 34
                slot_gap = 6
                slot_y = chip_y + (chip_h - icon_size) // 2
                vehicle_slot = (chip_x + chip_w - 8 - icon_size, slot_y, chip_x + chip_w - 8, slot_y + icon_size)
                role_slot = (
                    vehicle_slot[0] - slot_gap - icon_size,
                    slot_y,
                    vehicle_slot[0] - slot_gap,
                    slot_y + icon_size,
                )

                draw.rounded_rectangle(
                    role_slot,
                    radius=7,
                    fill=CARD_COLORS["slot_bg"],
                    outline=CARD_COLORS["slot_border"],
                    width=1,
                )
                if role_icon_name:
                    icon = _load_icon(ICON_DIR / role_icon_name, (30, 30))
                    if icon is not None:
                        icon_x = role_slot[0] + (icon_size - icon.width) // 2
                        icon_y = role_slot[1] + (icon_size - icon.height) // 2
                        image.paste(icon, (icon_x, icon_y), icon)
                else:
                    draw.text((role_slot[0] + 11, role_slot[1] + 8), "+", fill=CARD_COLORS["muted"], font=text_font)

                draw.rounded_rectangle(
                    vehicle_slot,
                    radius=7,
                    fill=CARD_COLORS["slot_bg"],
                    outline=vehicle_color,
                    width=2,
                )
                if vehicle_icon_name:
                    icon = _load_icon(VEHICLE_DIR / vehicle_icon_name, (30, 30))
                    if icon is not None:
                        icon_x = vehicle_slot[0] + (icon_size - icon.width) // 2
                        icon_y = vehicle_slot[1] + (icon_size - icon.height) // 2
                        image.paste(icon, (icon_x, icon_y), icon)
                else:
                    draw.text((vehicle_slot[0] + 10, vehicle_slot[1] + 9), "V", fill=CARD_COLORS["muted"], font=mini_font)

                text_x = chip_x + 8
                text_w = role_slot[0] - text_x - 8
                player_text = _truncate(draw, player_name, text_font, text_w)
                draw.text((text_x, chip_y + 10), player_text, fill=CARD_COLORS["text"], font=text_font)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _build_lineup_images(game: ScheduleGame) -> list[tuple[int, bytes]]:
    assignments = list(game.assignments.all())
    if not assignments:
        return []

    by_page: dict[int, dict[int, GameCellAssignment]] = {1: {}, 2: {}}
    for assignment in assignments:
        page = assignment.page_number if assignment.page_number in (1, 2) else 1
        by_page.setdefault(page, {})[assignment.cell_index] = assignment
    result: list[tuple[int, bytes]] = []
    for page in (1, 2):
        page_image = _build_page_lineup_image(game, page, by_page.get(page, {}))
        if page_image:
            result.append((page, page_image))
    return result


async def _has_reminder_marker(thread: discord.abc.Messageable, bot_user_id: int) -> bool:
    async for message in thread.history(limit=50):
        if message.author.id == bot_user_id and REMINDER_MARKER in (message.content or ""):
            return True
    return False


def _normalize_role_name(value: str) -> str:
    return " ".join((value or "").casefold().split())


def _resolve_role_mentions(guild: discord.Guild) -> str:
    normalized_to_role = {
        _normalize_role_name(role.name): role
        for role in guild.roles
    }

    mentions = []
    for role_name in ROLE_PING_NAMES:
        role = normalized_to_role.get(_normalize_role_name(role_name))
        mentions.append(role.mention if role else f"@{role_name}")
    return " ".join(mentions)


async def _send_reminders(bot_client: commands.Bot):
    games = await _get_upcoming_games()
    for game in games:
        page_images = _build_lineup_images(game)
        if not page_images:
            continue

        try:
            channel = await bot_client.fetch_channel(game.discord_thread_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            continue

        if not isinstance(channel, discord.Thread):
            continue

        if await _has_reminder_marker(channel, bot_client.user.id):
            continue

        start_str = timezone.localtime(game.game_start_time).strftime("%d.%m.%Y %H:%M")
        role_mentions = _resolve_role_mentions(channel.guild)
        caption = (
            f"Line up на игру **{game.name}**, старт во **{start_str}**.\n"
            f"{role_mentions}"
        )
        files = [
            discord.File(BytesIO(image_bytes), filename=f"lineup_game_{game.id}_page_{page}.png")
            for page, image_bytes in page_images
        ]
        await channel.send(content=caption, files=files)


async def run_two_hours_reminder():
    bot_client = commands.Bot(command_prefix="!", intents=intents)

    @bot_client.event
    async def on_ready():
        try:
            await _send_reminders(bot_client)
        finally:
            await bot_client.close()

    await bot_client.start(TOKEN)
