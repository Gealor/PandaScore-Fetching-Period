from datetime import UTC
from datetime import datetime
from typing import Sequence

from sqlalchemy import Select
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logger import log
from src.models.outbox_event import OutboxEvent
from src.models.outbox_event import StatusEnum
from src.schemas.exceptions.database import DatabaseException
from src.schemas.exceptions.outbox_event import OutboxEventNotFoundException


class OutboxEventRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    def _paginated_result(self, stmt: Select, page: int, per_page: int):
        return stmt.offset((page-1) * per_page).limit(per_page)

    async def get_all_events(
        self,
        page: int,
        per_page: int
    ) -> Sequence[OutboxEvent]:
        stmt = select(OutboxEvent).order_by(OutboxEvent.id.asc())

        stmt = self._paginated_result(stmt, page=page, per_page=per_page)

        result = await self.db_session.scalars(stmt)
        return result.all()

    async def get_events_by_status(
        self,
        page: int,
        per_page: int,
        status: StatusEnum
    ) -> Sequence[OutboxEvent]:
        stmt = (
            select(OutboxEvent).where(OutboxEvent.status == status)
            .order_by(OutboxEvent.id.asc())
        )

        stmt = self._paginated_result(stmt, page=page, per_page=per_page)

        result = await self.db_session.scalars(stmt)
        return result.all()

    async def update_status_by_id(self, id: int, status: StatusEnum) -> OutboxEvent:
        stmt = (
            update(OutboxEvent).values(status=status)
            .where(OutboxEvent.id == id)
            .returning(OutboxEvent)
        )
        try:
            event = await self.db_session.scalar(stmt)
        except IntegrityError as e:
            log.error("Failed to mark outbox event as sent: %s", e)
            raise DatabaseException from e

        if event is None:
            raise OutboxEventNotFoundException

        log.info("Outbox event marked as sent: id=%s", event.id)
        return event



    async def get_by_id(self, event_id: int) -> OutboxEvent | None:
        stmt = select(OutboxEvent).where(OutboxEvent.id == event_id)
        return await self.db_session.scalar(stmt)

    async def get_retriable_events(
        self, max_attempts: int = settings.max_attempts, limit: int = 100
    ) -> Sequence[OutboxEvent]:
        stmt = (
            select(OutboxEvent)
            .where(
                OutboxEvent.status == StatusEnum.pending,
                OutboxEvent.attempts < max_attempts,
            )
            .order_by(OutboxEvent.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True) # блокируем строки для обновления. Если какая-то транзакция параллельно попытается взять заблокированные строки, то она просто их пропустит
        )
        result = await self.db_session.scalars(stmt)
        return result.all()

    async def create_event(self, external_id: int, payload: dict) -> OutboxEvent:
        event = OutboxEvent(external_id=external_id, payload=payload)
        self.db_session.add(event)

        try:
            await self.db_session.flush()
        except IntegrityError as e:
            log.error("Failed to create outbox event: %s", e)
            raise DatabaseException from e

        await self.db_session.refresh(event)
        log.info("Outbox event created: id=%s external_id=%s", event.id, external_id)
        return event

    async def mark_sent(self, event_id: int) -> OutboxEvent:
        stmt = (
            update(OutboxEvent)
            .values(status=StatusEnum.sent, sent_at=datetime.now(UTC))
            .where(OutboxEvent.id == event_id)
            .returning(OutboxEvent)
        )

        try:
            event = await self.db_session.scalar(stmt)
        except IntegrityError as e:
            log.error("Failed to mark outbox event as sent: %s", e)
            raise DatabaseException from e

        if event is None:
            raise OutboxEventNotFoundException

        log.info("Outbox event marked as sent: id=%s", event.id)
        return event

    async def register_failed_attempt(
        self, event_id: int, max_attempts: int = settings.max_attempts
    ) -> OutboxEvent:
        event = await self.get_by_id(event_id)
        if event is None:
            raise OutboxEventNotFoundException

        event.attempts += 1
        if event.attempts >= max_attempts:
            event.status = StatusEnum.failed
            log.error(
                "Outbox event exceeded max attempts: id=%s external_id=%s attempts=%s",
                event.id,
                event.external_id,
                event.attempts,
            )

        try:
            await self.db_session.flush()
        except IntegrityError as e:
            log.error("Failed to update outbox event attempt: %s", e)
            raise DatabaseException from e

        return event

    async def delete_sent_before(self, before: datetime) -> int:
        stmt = (
            delete(OutboxEvent)
            .where(
                OutboxEvent.status == StatusEnum.sent,
                OutboxEvent.sent_at < before,
            )
            .returning(OutboxEvent.id)
        )

        try:
            result = (await self.db_session.scalars(stmt)).all()
        except IntegrityError as e:
            log.error("Failed to cleanup sent outbox events: %s", e)
            raise DatabaseException from e

        log.info("Deleted %s sent outbox events older than %s", len(result), before)
        return len(result)

