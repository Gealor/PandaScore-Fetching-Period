from datetime import datetime
from typing import Literal

from pydantic import AliasChoices
from pydantic import Field

from src.schemas.base import Base
from src.schemas.pandascore.streams import Stream

from .league_and_tournament import League
from .league_and_tournament import Tournament
from .opponents import Opponents
from .results import PlayerResult
from .results import TeamResult
from .videogame import Videogame


class MatchPostDTO(Base):
    external_id: int = Field(validation_alias=AliasChoices("id", "external_id"))
    external_source: str = "pandascore"
    slug: str
    status: Literal["not_started", "running", "finished", "canceled", "postponed"]
    scheduled_at: datetime | None = None
    begin_at: datetime | None = None
    end_at: datetime | None = None
    videogame: Videogame
    league: League
    tournament: Tournament
    opponents: list[Opponents]
    winner_id: int | None
    results: list[PlayerResult | TeamResult]
    streams_list: list[Stream]
    modified_at: datetime     # для версионности при upsert


class ListMatchDTO(Base):
    count: int = Field(ge=0)
    items: list[MatchPostDTO]
