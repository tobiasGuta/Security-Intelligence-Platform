import dramatiq
from dramatiq.brokers.redis import RedisBroker
from pydantic_settings import BaseSettings, SettingsConfigDict
import structlog
import os

class Settings(BaseSettings):
    REDIS_URL: str
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

redis_broker = RedisBroker(url=settings.REDIS_URL)
dramatiq.set_broker(redis_broker)

logger = structlog.get_logger()
logger.info("Worker starting up with Redis broker", redis_url=settings.REDIS_URL)

import app.actors
