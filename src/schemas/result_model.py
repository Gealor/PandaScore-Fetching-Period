from datetime import datetime

from pydantic import BaseModel
from pydantic import Field

from .base import Base


class BatchProcessingResult(BaseModel):
    new_events_count: int = Field(ge=0)
    max_modified_in_batch: datetime
    reached_old_data: bool