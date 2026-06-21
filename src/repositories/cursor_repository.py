from datetime import datetime

from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logger import log
from src.models.cursor import Cursor
from src.schemas.exceptions.cursor import CursorNotFoundException
from src.schemas.exceptions.database import DatabaseException


class CursorRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_cursor_by_name(self, name: str) -> Cursor | None:
        stmt = select(Cursor).where(Cursor.job_name == name)

        result = await self.db_session.scalar(stmt)

        return result

    async def create_cursor(self, last_modified_at: datetime, name: str) -> Cursor:
        cursor = Cursor(
            job_name=name,
            last_modified_at=last_modified_at,
        )

        self.db_session.add(cursor)

        try:
            await self.db_session.flush()
        except IntegrityError as e:
            log.error("Failed to add cursor: %s", e)
            raise DatabaseException from e

        log.info(
            "Cursor created with name=%s: %s", cursor.job_name, cursor.last_modified_at
        )
        return cursor

    async def update_cursor(self, last_modified_at: datetime, name: str) -> Cursor:
        stmt = (
            update(Cursor)
            .values(last_modified_at=last_modified_at)
            .where(Cursor.job_name == name)
            .returning(Cursor)
        )

        try:
            cursor = await self.db_session.scalar(stmt)
        except IntegrityError as e:
            log.error("Failed to update cursor: %s", e)
            raise DatabaseException from e

        if cursor is None:
            raise CursorNotFoundException

        log.info(
            "Update cursor with name=%s: %s", cursor.job_name, cursor.last_modified_at
        )
        return cursor

    async def delete_cursor(self, name: str) -> None:
        stmt = delete(Cursor).where(Cursor.job_name == name)

        await self.db_session.execute(stmt)

        try:
            await self.db_session.flush()
        except IntegrityError as e:
            log.error("Failed to delete cursor: %s", e)
            raise DatabaseException from e

        log.info("Deleted cursor with name=%s", name)
