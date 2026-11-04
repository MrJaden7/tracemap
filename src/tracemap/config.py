"""Runtime settings, read from environment variables or a .env file in the repo root."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv_into_os_environ() -> None:
    """Load every `.env` line into os.environ so unprefixed variables like
    ANTHROPIC_API_KEY reach any third-party library that reads the environment
    directly. Only sets variables that are not already present; never overrides."""
    env_path = REPO_ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv_into_os_environ()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TRACEMAP_",
        env_file=REPO_ROOT / ".env",
        extra="ignore",
    )

    db_host: str = "localhost"
    db_port: int = 5440
    db_name: str = "tracemap"
    db_user: str = "tracemap"
    db_password: str = "tracemap"

    vocab_dir: Path = REPO_ROOT / "data" / "vocab"
    synthea_dir: Path = REPO_ROOT / "data" / "synthea"

    @property
    def conninfo(self) -> str:
        return (
            f"host={self.db_host} port={self.db_port} dbname={self.db_name} "
            f"user={self.db_user} password={self.db_password}"
        )


def get_settings() -> Settings:
    return Settings()
