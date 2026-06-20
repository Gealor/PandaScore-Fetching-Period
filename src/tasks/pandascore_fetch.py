from src.core.celery import celery
from src.core.database import async_session_maker
from src.core.logger import log


@celery.task
def fetch_matches():
    log.info("Получение данных")
