from src.schemas.base import Base


# Видеоигра
class Videogame(Base):
    id: int
    name: str
    slug: str | None = None
