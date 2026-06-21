from typing import Callable

from src.repositories.cursor_repository import CursorRepository
from src.repositories.outbox_repository import OutboxEventRepository

from .database import async_session_maker


class UnitOfWork:
    def __init__(self, session_factory: Callable):
        self.session_factory = session_factory

    async def __aenter__(self):
        self.session = self.session_factory()
        self.cursor_repo = CursorRepository(self.session)
        self.outbox_repo = OutboxEventRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        else:
            try:
                await self.commit()
            except Exception as e:
                await self.rollback()
                raise e

        await self.session.close()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()


async def get_uow():
    uow = UnitOfWork(session_factory=async_session_maker)
    return uow