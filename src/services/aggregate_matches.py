import asyncio
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any

import aio_pika
from aiohttp import ClientSession
from aiohttp import ClientTimeout
from pydantic import ValidationError

from src.core.config import settings
from src.core.database import async_session_maker
from src.core.logger import log
from src.core.uow import UnitOfWork
from src.integrations.pandascore_api import get_list_matches
from src.schemas.pandascore.match_dto import MatchPostDTO
from src.utils.publish_event import get_exchange
from src.utils.publish_event import publish_match


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


# TODO: декомпозировать, слишком тяжелая функция
async def fetch_and_store_new_matches(
    http_session: ClientSession,
    uow: UnitOfWork,
) -> None:
    since = await get_or_create_cursor(uow)
    fetch_since = since - settings.cursor_overlap

    page = 1
    max_modified = since
    new_events_count = 0
    reached_old_data = False

    while not reached_old_data:
        log.info("Fetching API page #%d...", page)
        batch = await get_list_matches(
            http_session, page=page, per_page=settings.api.per_page
        )

        if not batch:
            break

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

        if len(batch) < settings.api.per_page:
            break

        page += 1

    if new_events_count > 0:
        await uow.cursor_repo.update_cursor(max_modified, settings.cursor_name)
        log.info(
            "Successfully fetched %d new matches and updated cursor to %s",
            new_events_count,
            max_modified,
        )
    else:
        log.info("No new matches found.")

# TODO: сделать так, что если ошибка случилась по вине инфраструктуры (упал брокер или что-то такое), то мы НЕ инкрементируем попытки, а просто логируем критическим уровнем и прерываем задачу полностью
async def publish_pending_events(
    channel: aio_pika.abc.AbstractChannel,
    exchange: aio_pika.abc.AbstractExchange,
    batch_size: int = 100,
) -> None:
    total_published = 0

    while True:
        async with UnitOfWork(session_factory=async_session_maker) as uow:
            pending_events = await uow.outbox_repo.get_retriable_events(
                settings.max_attempts, limit=batch_size
            )

            if not pending_events:
                break

            log.info("Publishing batch of %d pending events...", len(pending_events))

            for event in pending_events:
                try:
                    match = MatchPostDTO.model_validate(event.payload)
                    await publish_match(channel, exchange, match)
                    await uow.outbox_repo.mark_sent(event.id)
                    total_published += 1
                except ValidationError as e:
                    log.error("Permanent data validation error for event_id=%s: %s. Marking attempt.", event.id, e)
                    await uow.outbox_repo.register_failed_attempt(
                        event.id, settings.max_attempts
                    )
                except (
                    aio_pika.exceptions.AMQPError,  # Базовый класс для всех ошибок aio-pika (ConnectionClosed, ChannelClosed)
                    IOError,                        # Ошибки ввода-вывода (включая ConnectionResetError, BrokenPipeError)
                    OSError,                        # Системные ошибки сокетов
                    asyncio.TimeoutError,           # Таймаут ожидания подтверждения публикации
                ) as net_err:
                    log.critical(
                        "Infrastructure error (RabbitMQ/Network) during publish: %s. Aborting entire job.",
                        net_err
                    )
                    raise
                except Exception as app_exc:
                    log.warning("Publish failed for event_id=%s: %s", event.id, app_exc)
                    await uow.outbox_repo.register_failed_attempt(
                        event.id, settings.max_attempts
                    )

    if total_published > 0:
        log.info("Successfully published %d total events in this run.", total_published)


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
            async with UnitOfWork(session_factory=async_session_maker) as fetch_uow:
                await fetch_and_store_new_matches(http_session, fetch_uow)

            # ЭТАП 2: Отправка событий.
            await publish_pending_events(channel, exchange)

            # ЭТАП 3: Очистка старых событий.
            async with UnitOfWork(session_factory=async_session_maker) as clean_uow:
                cleanup_threshold = datetime.now(UTC) - timedelta(days=7)
                await clean_uow.outbox_repo.delete_sent_before(cleanup_threshold)

        except Exception as e:
            log.exception("Job process_matches encountered a fatal error: %s", e)
            raise
