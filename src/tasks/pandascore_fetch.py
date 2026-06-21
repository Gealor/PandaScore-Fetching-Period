import asyncio

from src.core.celery import celery
from src.services.aggregate_matches import process_matches


@celery.task
def fetch_matches():
    asyncio.run(process_matches())
