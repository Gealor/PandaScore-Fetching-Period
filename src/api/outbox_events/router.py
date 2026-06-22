from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from src.core.logger import log
from src.core.uow import UnitOfWork
from src.core.uow import get_uow_dep
from src.models.outbox_event import StatusEnum
from src.schemas.exceptions.outbox_event import OutboxEventNotFoundException
from src.schemas.outbox_event import ListOutboxEventSchema
from src.schemas.outbox_event import OutboxEventSchema
from src.services.outbox_service import OutboxEventService

router = APIRouter(prefix="/outbox")


@router.get("")
async def get_outbox_events(
    page: int,
    per_page: int = 100,
    status: StatusEnum | None = None,
    uow: UnitOfWork = Depends(get_uow_dep),
) -> ListOutboxEventSchema:
    return await OutboxEventService(uow).get_outbox_events(
        page=page, per_page=per_page, status=status
    )

@router.patch("/{id}")
async def update_status_by_id(
    id: int,
    new_status: StatusEnum,
    uow: UnitOfWork = Depends(get_uow_dep),
) -> OutboxEventSchema:
    try:
        result = await OutboxEventService(uow).update_status_by_id(id=id, status=new_status)
    except OutboxEventNotFoundException:
        log.info("Outbox event by id=%d not found", id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found"
        ) from None

    return result
