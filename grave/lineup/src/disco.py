import os
import django

import discord
from discord.ext import commands
from dotenv import load_dotenv

from lineup.src.sync_to_db import save_game_to_db

load_dotenv()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "grave.settings")
django.setup()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

GUILD_ID = 1316440570129944586
FORUM_CHANNEL_ID = 1349700668558016573

intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


async def sync_games_to_db():
    guild = await bot.fetch_guild(GUILD_ID)
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

        await save_game_to_db(
            thread.id,
            thread.name,
            thread.archived,
            tags,
            thread.created_at,
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
