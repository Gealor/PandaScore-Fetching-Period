import asyncio

from src.core.celery import celery
from src.services.aggregate_matches import process_matches


@celery.task(acks_late=True, reject_on_worker_lost=True)
def fetch_matches():
    asyncio.run(process_matches())
