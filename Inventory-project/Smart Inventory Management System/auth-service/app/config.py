"""
Auth Service – Application Configuration
Loads settings from environment variables / .env file.
"""
from functools import lru_cache
from urllib.parse import quote_plus
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────
    app_name: str = "Auth Service"
    app_version: str = "1.0.0"
    app_env: str = "development"
    debug: bool = True
    allowed_origins: str = "http://localhost:5173,http://localhost:8000"

    # ── Database ─────────────────────────────────────────────────────────
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str
    db_password: str
    db_name: str = "smart_inventory_auth"

    # ── JWT ──────────────────────────────────────────────────────────────
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Optional credentials used only to create missing local bootstrap accounts.
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    bootstrap_manager_email: str | None = None
    bootstrap_manager_password: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        # URL-encode password to handle special characters like @, #, etc.
        encoded_password = quote_plus(self.db_password)
        return (
            f"mysql+pymysql://{self.db_user}:{encoded_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
