from datetime import datetime
from typing import List

from pydantic import Field

from src.models.outbox_event import StatusEnum

from .base import Base


class OutboxEventSchema(Base):
    id: int = Field(examples=[1, 2, 3])
    external_id: int = Field(examples=[12456567,])
    payload: dict
    status: StatusEnum = Field(examples=[StatusEnum.failed, StatusEnum.pending, StatusEnum.sent])
    created_at: datetime
    sent_at: datetime | None
    attempts: int = Field(ge=0)


class ListOutboxEventSchema(Base):
    count: int = Field(ge=0)
    items: List[OutboxEventSchema]


class OutboxEventUpdateSchema(Base):
    status: StatusEnum = Field(examples=[StatusEnum.failed, StatusEnum.pending, StatusEnum.sent])
