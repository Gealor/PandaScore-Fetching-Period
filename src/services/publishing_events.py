import asyncio

import aio_pika
from pydantic import ValidationError

from src.core.config import settings
from src.core.database import async_session_maker
from src.core.logger import log
from src.core.uow import UnitOfWork
from src.models.outbox_event import OutboxEvent
from src.schemas.pandascore.match_dto import MatchPostDTO
from src.utils.aiopika_publishing import publish_match


async def publish_one_event(
    exchange: aio_pika.abc.AbstractExchange,
    uow: UnitOfWork,
    event: OutboxEvent
) -> bool:
    try:
        match = MatchPostDTO.model_validate(event.payload)
        await publish_match(exchange, match)
        await uow.outbox_repo.mark_sent(event.id)
    except ValidationError as e:
        log.error("Permanent data validation error for event_id=%s: %s. Marking attempt.", event.id, e)
        await uow.outbox_repo.register_failed_attempt(
            event.id, settings.max_attempts
        )
        return False
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
        return False

    return True

# (СДЕЛАНО) TODO: сделать так, что если ошибка случилась по вине инфраструктуры (упал брокер или что-то такое), то мы НЕ инкрементируем попытки, а просто логируем критическим уровнем и прерываем задачу полностью
async def publish_pending_events(
    exchange: aio_pika.abc.AbstractExchange,
    batch_size: int = 100,
) -> None:
    total_published = 0

    while True:
        # обработали одну страницу успешно, обозначили их в таблице как отправленные, чтобы если упала следующая пачка, это не откатилось
        async with UnitOfWork(session_factory=async_session_maker) as uow:
            pending_events = await uow.outbox_repo.get_retriable_events(
                settings.max_attempts, limit=batch_size
            )

            if not pending_events:
                break

            log.info("Publishing batch of %d pending events...", len(pending_events))

            for event in pending_events:
                published = await publish_one_event(
                    exchange,
                    uow,
                    event,
                )
                if published:
                    total_published += 1

    if total_published > 0:
        log.info("Successfully published %d total events in this run.", total_published)
