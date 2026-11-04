"""Runtime settings, read from environment variables or a .env file in the repo root."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


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
