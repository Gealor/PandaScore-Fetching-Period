from typing import Literal

from src.schemas.base import Base


# Лига
class League(Base):
    id: int
    name: str
    slug: str | None = None
    image_url: str | None = None


# Турнир
class Tournament(Base):
    name: str
    tier: Literal["s", "a", "b", "c", "d", "unranked"]
    winner_id: int | None = None
