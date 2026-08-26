import asyncio

from src.core.celery import celery
from src.core.thread_loop import celery_event_loop
from src.services.aggregate_matches import process_matches


@celery.task(acks_late=True, reject_on_worker_lost=True)
def fetch_matches():
    # asyncio.run(process_matches()) # костыль на каждый запуск задачи создавать event_loop, проблема с соединениями в БД (надо создавать новый engine для каждого запуска)
    celery_event_loop.run(process_matches())
