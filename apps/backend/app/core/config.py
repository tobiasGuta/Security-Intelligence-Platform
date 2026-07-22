from typing import Literal, List
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    APP_ENV: Literal["development", "production"] = "development"
    SECRET_KEY: str = Field(min_length=32)
    SESSION_SECRET: str = Field(min_length=32)
    SESSION_IDLE_HOURS: int = 4
    SESSION_ABS_HOURS: int = 24
    CORS_ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    RATE_LIMIT_LOGIN_ATTEMPTS: int = 10
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 900
    NVD_INITIAL_SYNC_DAYS: int = 120
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings() # type: ignore[call-arg]
