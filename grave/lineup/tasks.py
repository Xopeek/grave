from celery import shared_task
from lineup.src.apollo import sync_apollo
from lineup.src.disco import sync_disco



@shared_task(ignore_result=True)
def run_discord_sync():
    sync_apollo()
    sync_disco()
