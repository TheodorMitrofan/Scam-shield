"""Runtime settings (CLAUDE.md §4.3). Values come from env vars / a local .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+psycopg://scam:scam@localhost:5432/scamshield"
    cors_origins: str = "http://localhost:4200"
    model_dir: str = "models/scam-bert"
    storage_dir: str = "data"
    kit_dir: Path = REPO_ROOT / "Scam_Shield_Public_Kit"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
