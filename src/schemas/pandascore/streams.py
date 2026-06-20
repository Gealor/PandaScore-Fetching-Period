from typing import Literal

from src.schemas.base import Base


class Stream(Base):
    main: bool
    official: bool # если True, то и main будет True
    raw_url: str
