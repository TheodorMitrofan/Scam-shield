"""Runtime settings (CLAUDE.md §4.3). Values come from env vars / a local .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+psycopg://scam:scam@localhost:5544/scamshield"
    cors_origins: str = "http://localhost:4200"
    model_dir: str = "models/scam-bert"
    storage_dir: str = "data"
    kit_dir: Path = REPO_ROOT / "Scam_Shield_Public_Kit"

    # Fraud-report e-mail (demo). Password = Gmail App Password, ONLY in backend/.env (never committed).
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = "palrobertogiulio@gmail.com"
    smtp_password: str = ""

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
