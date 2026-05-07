from celery import shared_task
import asyncio
from lineup.src.apollo import sync_apollo
from lineup.src.disco import sync_disco



@shared_task(ignore_result=True)
def run_discord_sync():
    asyncio.run(sync_disco())
    asyncio.run(sync_apollo())
