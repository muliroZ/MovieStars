from functools import lru_cache

from pydantic import PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações carregadas de variáveis de ambiente ou do arquivo .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "RocketLab API"
    project_version: str = "2026.2"
    environment: str = "local"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite+aiosqlite:///./moviestars.db"
    backend_cors_origins: list[str] = ["http://localhost:5173"]
    log_level: str = "INFO"
    # Cache das consultas do catálogo e dos gêneros (feature 101, plan DEC-7).
    cache_enabled: bool = True
    cache_ttl_seconds: PositiveInt = 300
    cache_max_entries: PositiveInt = 256


@lru_cache
def get_settings() -> Settings:
    return Settings()
