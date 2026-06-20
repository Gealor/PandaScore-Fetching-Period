from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from .base import Base


class Cursor(Base):
    __tablename__ = "cursors"

    job_name: Mapped[str] = mapped_column(primary_key=True)
    last_modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
