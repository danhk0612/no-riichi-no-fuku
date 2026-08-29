from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str | None = None
    postgres_db: str = "no_riichi_no_fuku"
    postgres_user: str = "nrnf"
    postgres_password: SecretStr | None = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    superadmin_login_id: str | None = None
    superadmin_initial_password: SecretStr | None = None
    media_root: Path = Path("/data/media")

    def require_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        if not self.postgres_password:
            raise RuntimeError("DATABASE_URL is required")
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)

    def require_superadmin_credentials(self) -> tuple[str, str]:
        if not self.superadmin_login_id or not self.superadmin_initial_password:
            raise RuntimeError(
                "SUPERADMIN_LOGIN_ID and SUPERADMIN_INITIAL_PASSWORD are required"
            )
        return (
            self.superadmin_login_id,
            self.superadmin_initial_password.get_secret_value(),
        )
