import os
import re
from datetime import timezone as dt_timezone
import django
from django.utils import timezone

import discord
from discord.ext import commands
from dotenv import load_dotenv

from lineup.src.sync_to_db import save_game_to_db

load_dotenv()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "grave.settings")
django.setup()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

FORUM_CHANNEL_ID = 1349700668558016573

intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


async def get_first_message(thread: discord.Thread) -> discord.Message | None:
    async for message in thread.history(limit=1, oldest_first=True):
        return message
    return None


def extract_game_start_time(msg: discord.Message | None):
    if not msg or not msg.embeds:
        return None

    embed = msg.embeds[0]
    for field in embed.fields:
        field_name = field.name.lower()
        if "time" not in field_name and "время" not in field_name:
            continue

        timestamp_match = re.search(r"<t:(\d+):[tTdDfFR]>", field.value)
        if timestamp_match:
            try:
                unix_ts = int(timestamp_match.group(1))
                dt = timezone.localtime(
                    timezone.datetime.fromtimestamp(unix_ts, tz=dt_timezone.utc)
                )
                return dt.replace(second=0, microsecond=0)
            except (ValueError, OSError, OverflowError):
                pass

    return None


async def sync_games_to_db():
    forum = await bot.fetch_channel(FORUM_CHANNEL_ID)

    if not isinstance(forum, discord.ForumChannel):
        return

    threads = list(forum.threads)
    async for t in forum.archived_threads(limit=None):
        threads.append(t)

    for thread in threads:
        if not thread.created_at:
            continue

        tags = ", ".join(tag.name for tag in thread.applied_tags)
        first_message = await get_first_message(thread)
        game_start_time = extract_game_start_time(first_message)
        print(game_start_time)

        await save_game_to_db(
            thread.id,
            thread.name,
            thread.archived,
            tags,
            thread.created_at,
            game_start_time,
        )


async def sync_disco():
    @bot.event
    async def on_ready():
        print("Sync games")
        try:
            await sync_games_to_db()
        finally:
            await bot.close()

    await bot.start(TOKEN)
