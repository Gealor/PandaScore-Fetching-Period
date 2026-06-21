from celery import Celery

from .config import settings


def prepare_celery() -> Celery:
    celery = Celery(
        "src.core.celery",
        broker=settings.rabbitmq.rabbitmq_url,
        backend="rpc://",
        include=[
            "src.tasks.pandascore_fetch",
        ],
    )
    celery.conf.beat_schedule = {
        "fetch_matches": {
            "task": "src.tasks.pandascore_fetch.fetch_matches",
            "schedule": settings.celery.cron_tab,
        }
    }

    return celery


celery = prepare_celery()
