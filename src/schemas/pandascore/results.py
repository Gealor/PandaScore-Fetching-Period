from pydantic import Field

from src.schemas.base import Base


# Результаты игрока
class PlayerResult(Base):
    player_id: int
    score: int = Field(ge=0)

# Результаты команды
class TeamResult(Base):
    team_id: int
    score: int = Field(ge=0)
