from src.core.uow import UnitOfWork
from src.models.outbox_event import StatusEnum
from src.schemas.outbox_event import ListOutboxEventSchema
from src.schemas.outbox_event import OutboxEventSchema


class OutboxEventService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_outbox_events(
        self, page: int, per_page: int, status: StatusEnum | None = None,
    ) -> ListOutboxEventSchema:
        result = (
            await self.uow.outbox_repo.get_all_events(page, per_page)
            if status is None else
            await self.uow.outbox_repo.get_events_by_status(page, per_page, status)
        )

        return ListOutboxEventSchema(
            count=len(result),
            items=[OutboxEventSchema.model_validate(elem) for elem in result],
        )

    async def update_status_by_id(self, id: int, status: StatusEnum) -> OutboxEventSchema:
        result = await self.uow.outbox_repo.update_status_by_id(id=id, status=status)
        return OutboxEventSchema.model_validate(result)