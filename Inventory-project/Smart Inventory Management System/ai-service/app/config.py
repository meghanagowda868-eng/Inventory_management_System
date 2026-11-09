"""AI Service configuration."""
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Service"
    app_version: str = "1.0.0"
    app_env: str = "development"
    allowed_origins: str = "http://localhost:5173,http://localhost:8000"

    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"

    inventory_service_url: str = "http://localhost:8002"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
