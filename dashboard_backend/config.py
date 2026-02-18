"""Configuration management for the dashboard backend."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/epstein_rag"

    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    debug: bool = False

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # WebSocket
    ws_heartbeat_interval: int = 30  # seconds

    # Pagination defaults
    default_page_size: int = 50
    max_page_size: int = 200

    model_config = {"env_prefix": "DASHBOARD_", "env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
