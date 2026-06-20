from typing import Literal

from src.schemas.base import Base


# детальная информация об оппоненте
class Opponent(Base):
    id: int
    name: str
    acronym: str | None
    image_url: str | None


# Оппоненты с типом
class Opponents(Base):
    type: Literal["Player", "Team"]
    opponent: Opponent
