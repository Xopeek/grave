import os
import django
import re

import discord
from discord.ext import commands
from dotenv import load_dotenv

from lineup.src.sync_to_db import save_participants

load_dotenv()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "grave.settings")
django.setup()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

GUILD_ID = 1316440570129944586
FORUM_CHANNEL_ID = 1349700668558016573

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


def build_member_map(guild):
    return {
        m.display_name.lower(): m
        for m in guild.members
    }


async def get_first_message(thread: discord.Thread) -> discord.Message | None:
    async for message in thread.history(limit=1, oldest_first=True):
        return message
    return None


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


async def handle_thread(thread, member_map):
    msg = await get_first_message(thread)
    if not msg or not msg.embeds:
        return

    embed = msg.embeds[0]

    statuses = {
        "Accepted": [],
        "Tentative": [],
        "Waitlist": [],
    }

    for field in embed.fields:
        for s in statuses:
            if s in field.name:
                statuses[s] = parse_embed_field_value(field.value)

    await save_participants(thread.id, statuses, member_map)


async def sync():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        guild = await bot.fetch_guild(GUILD_ID)

    forum = await bot.fetch_channel(FORUM_CHANNEL_ID)
    if not isinstance(forum, discord.ForumChannel):
        print("not forum")
        return

    member_map = build_member_map(guild)

    threads = list(forum.threads)
    async for t in forum.archived_threads(limit=None):
        threads.append(t)

    for thread in threads:
        await handle_thread(thread, member_map)


async def sync_apollo():
    @bot.event
    async def on_ready():
        print("Apollo sync started")
        try:
            await sync()
        finally:
            await bot.close()

    await bot.start(TOKEN)
