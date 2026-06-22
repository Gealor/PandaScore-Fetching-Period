import logging
from datetime import timedelta
from pathlib import Path
from typing import Annotated

from celery.schedules import crontab
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR.parent / ".env"
ENV_TEMPLATE = BASE_DIR.parent / ".env.template"


class RuntimeSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ENV_TEMPLATE, ENV_FILE),
        case_sensitive=False,
        extra="ignore",  # Игнорировать другие переменные в .env
    )

    db_name: Annotated[str, Field(alias="POSTGRES_DB")]
    db_user: Annotated[str, Field(alias="POSTGRES_USER")]
    db_password: Annotated[str, Field(alias="POSTGRES_PASSWORD")]
    db_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    db_port: int = Field(default=6000, alias="PGPORT")
    db_echo: bool = False

    @property
    def db_url(self):
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ENV_TEMPLATE, ENV_FILE),
        case_sensitive=False,
        extra="ignore",  # Игнорировать другие переменные в .env
    )

    host: Annotated[str, Field(alias="REDIS_HOST")]
    port: Annotated[int, Field(alias="REDIS_PORT")]


class RabbitMQSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ENV_TEMPLATE, ENV_FILE),
        case_sensitive=False,
        extra="ignore",  # Игнорировать другие переменные в .env
    )

    rabbit_protocol: str = "amqp"
    rabbit_host: Annotated[str, Field(alias="RABBITMQ_HOST")]
    rabbit_port: Annotated[str, Field(alias="RABBITMQ_PORT")]
    rabbit_user: Annotated[str, Field(alias="RABBITMQ_USER")]
    rabbit_password: Annotated[str, Field(alias="RABBITMQ_PASSWORD")]

    @property
    def rabbitmq_url(self):
        return (
            f"{self.rabbit_protocol}://{self.rabbit_user}:{self.rabbit_password}@"
            f"{self.rabbit_host}:{self.rabbit_port}"
        )


class CelerySettings(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True) # разрешить сторонние типы данных, помимо моделей pydantic и примитивов.

    countdown_seconds: int = 10
    cron_tab: crontab = crontab(minute=00, hour="*")  # каждый час в 00 минут


class LoggerSettings(BaseModel):
    LOG_DEFAULT_FORMAT: str = "[%(asctime)s.%(msecs)03d] %(module)10s:%(lineno)-3d %(levelname)-7s - %(message)s"
    level: int = logging.INFO
    datefmt: str = "%Y-%m-%d %H:%M:%S"


class ExternalApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ENV_TEMPLATE, ENV_FILE),
        case_sensitive=False,
        extra="ignore",  # Игнорировать другие переменные в .env
    )

    api_token: Annotated[str, Field(alias="PANDASCORE_API_TOKEN")]
    base_url: str = "https://api.pandascore.co"
    timeout_seconds: int = 30
    per_page: int = 100

    attempts_for_retry: int = 5
    backoff_factor: float = 2.0


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ENV_TEMPLATE, ENV_FILE),
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
    )

    runtime: RuntimeSettings = RuntimeSettings()

    database: DatabaseSettings = Field(
        default_factory=DatabaseSettings,
    )
    redis: RedisSettings = Field(
        default_factory=RedisSettings,
    )

    log: LoggerSettings = LoggerSettings()

    rabbitmq: RabbitMQSettings = Field(default_factory=RabbitMQSettings)
    celery: CelerySettings = CelerySettings()

    api: ExternalApiSettings = Field(default_factory=ExternalApiSettings)

    max_attempts: int = 5
    cursor_overlap: timedelta = timedelta(minutes=5)
    cursor_name: str = "pandascore_matches"
    exchange_name: Annotated[str, Field(alias="EXCHANGE_NAME")]
    routing_key: Annotated[str, Field(alias="ROUTING_KEY")]


settings = Settings()
