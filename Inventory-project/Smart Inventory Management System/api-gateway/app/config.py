"""API Gateway configuration."""
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "API Gateway"
    app_version: str = "1.0.0"
    allowed_origins: str = "http://localhost:5173"

    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"

    auth_service_url: str = "http://localhost:8001"
    inventory_service_url: str = "http://localhost:8002"
    ai_service_url: str = "http://localhost:8003"

    request_timeout: int = 30

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
