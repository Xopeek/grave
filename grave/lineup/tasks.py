from celery import shared_task
import asyncio
from lineup.src.apollo import sync_apollo
from lineup.src.disco import sync_disco
from lineup.src.reminder import run_two_hours_reminder



@shared_task(ignore_result=True)
def run_discord_sync():
    asyncio.run(sync_disco())
    asyncio.run(sync_apollo())


@shared_task(ignore_result=True)
def run_game_two_hours_reminder():
    asyncio.run(run_two_hours_reminder())
