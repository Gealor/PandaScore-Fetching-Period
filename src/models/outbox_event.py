from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from .base import Base


class StatusEnum(str, Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[int]
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[StatusEnum] = mapped_column(
        SQLEnum(StatusEnum, native_enum=False, length=20), default=StatusEnum.pending
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    attempts: Mapped[int] = mapped_column(default=0)
