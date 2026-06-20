from pydantic import BaseModel
from pydantic import ConfigDict


class Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)
