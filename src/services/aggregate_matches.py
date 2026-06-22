from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any

import aio_pika
from aiohttp import ClientSession
from aiohttp import ClientTimeout
from pydantic import ValidationError

from src.core.config import settings
from src.core.database import engine
from src.core.logger import log
from src.core.uow import UnitOfWork
from src.core.uow import get_uow
from src.integrations.pandascore_api import get_list_matches
from src.schemas.exceptions.integration import BaseIntegrationException
from src.schemas.pandascore.match_dto import MatchPostDTO
from src.schemas.result_model import BatchProcessingResult
from src.services.publishing_events import publish_pending_events
from src.utils.aiopika_publishing import get_exchange


def validate_match_json(raw: dict[str, Any]) -> MatchPostDTO | None:
    try:
        match = MatchPostDTO.model_validate(raw)
    except ValidationError as e:
        log.error("Failed validate record: %s. Skipping...", e)
        return None

    return match


async def get_or_create_cursor(uow: UnitOfWork) -> datetime:
    cursor = await uow.cursor_repo.get_cursor_by_name(settings.cursor_name)
    if cursor is not None:
        return cursor.last_modified_at

    # первый запуск - курсора ещё нет, тогда стартуем НЕ с начала времен
    initial_value = datetime.now(UTC) - timedelta(days=1)
    created = await uow.cursor_repo.create_cursor(initial_value, settings.cursor_name)
    await uow.commit()
    return created.last_modified_at

async def update_cursor(
    total_events: int,
    max_modified_at: datetime,
    uow: UnitOfWork,
) -> None:
    if total_events > 0:
        await uow.cursor_repo.update_cursor(max_modified_at, settings.cursor_name)
        log.info(
            "Successfully fetched %d new matches and updated cursor to %s",
            total_events,
            max_modified_at,
        )
    else:
        log.info("No new matches found.")


async def process_match_batch(
    batch: list[dict[str, Any]],
    fetch_since: datetime,
    current_max_modified: datetime,
    uow: UnitOfWork,
) -> BatchProcessingResult:
    new_events_count = 0
    max_modified = current_max_modified
    reached_old_data = False

    for raw in batch:
        match = validate_match_json(raw)
        if not match:
            continue

        if match.modified_at <= fetch_since:
            reached_old_data = True
            break

        await uow.outbox_repo.create_event(
            match.external_id, match.model_dump(mode="json")
        )
        new_events_count += 1

        if match.modified_at > max_modified:
            max_modified = match.modified_at

    return BatchProcessingResult(
        new_events_count=new_events_count,
        max_modified_in_batch=max_modified,
        reached_old_data=reached_old_data,
    )


async def fetch_and_store_new_matches(
    http_session: ClientSession,
    uow: UnitOfWork,
) -> None:
    since = await get_or_create_cursor(uow)
    fetch_since = since - settings.cursor_overlap

    page = 1
    max_modified = since
    total_new_events = 0
    reached_old_data = False

    while not reached_old_data:
        log.info("Fetching API page #%d...", page)
        try:
            batch = await get_list_matches(
                http_session, page=page, per_page=settings.api.per_page
            )
        except BaseIntegrationException as e:
            log.error(
                "PandaScore API Error: Failed to fetch page #%d. "
                "Skipping this page and attempting to request the next one. Detail: %s",
                page,
                e,
            )
            page += 1
            continue

        if not batch:
            break

        result = await process_match_batch(
            batch=batch,
            fetch_since=fetch_since,
            current_max_modified=max_modified,
            uow=uow
        )

        total_new_events += result.new_events_count
        max_modified = result.max_modified_in_batch

        if result.reached_old_data or len(batch) < settings.api.per_page:  # последняя страница
            break

        page += 1

    await update_cursor(total_events=total_new_events, max_modified_at=max_modified, uow=uow)


async def process_matches():
    timeout = ClientTimeout(total=settings.api.timeout_seconds)
    connection = await aio_pika.connect_robust(settings.rabbitmq.rabbitmq_url)

    async with (
        ClientSession(timeout=timeout) as http_session,
        connection,
    ):
        channel = await connection.channel(publisher_confirms=True)
        exchange = await get_exchange(channel, settings.exchange_name)

        try:
            # ЭТАП 1: Синхронизация данных.
            async with get_uow() as fetch_uow:
                await fetch_and_store_new_matches(http_session, fetch_uow)

            # ЭТАП 2: Отправка событий.
            await publish_pending_events(channel, exchange)

            # ЭТАП 3: Очистка старых событий.
            async with get_uow() as clean_uow:
                cleanup_threshold = datetime.now(UTC) - timedelta(days=7)
                await clean_uow.outbox_repo.delete_sent_before(cleanup_threshold)

        except Exception as e:
            log.exception("Job process_matches encountered a fatal error: %s", e)
            raise
        finally:
            await engine.dispose() # нужно, чтобы закрыть ВСЕ соединения в пуле, чтобы избавиться от соедниений, привязанных к текущему событийному циклу (event_loop),
            # т.к. в celery задаче мы создаем НОВЫЙ event_loop, а engine, session_maker объявлены на уровне модуля и не ИНИЦИАЛИЗИРУЮТСЯ ЛЕНИВО
