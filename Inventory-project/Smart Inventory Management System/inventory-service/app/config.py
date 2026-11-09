"""Inventory Service configuration."""
from functools import lru_cache
from urllib.parse import quote_plus
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Inventory Service"
    app_version: str = "1.0.0"
    app_env: str = "development"
    debug: bool = True
    allowed_origins: str = "http://localhost:5173,http://localhost:8000"

    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str
    db_password: str
    db_name: str = "smart_inventory_products"

    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"

    festive_safety_stock_percent: float = 10.0
    festive_sales_trend_factor: float = 1.2
    festive_relevance_factor: float = 1.35
    festive_discount_demand_uplift_per_five_percent: float = 0.05

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
    return Settings()
