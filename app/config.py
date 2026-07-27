from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Grocery API"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    secret_key: str = "change-me-in-production"
    database_url: str = "sqlite+aiosqlite:///./grocery.db"
    allowed_origins: list[str] = [
        "https://sjssupermarket.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    r2_public_base_url: str = "https://pub-8091345920e34b7a919f744ff9900480.r2.dev"
    r2_product_image_variant: str = "l"
    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    firebase_credentials_path: str = ""
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    razorpay_api_base: str = "https://api.razorpay.com/v1"
    razorpay_currency: str = "INR"
    razorpay_environment: str = "test"

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str) and value.lower() in {"release", "production", "prod"}:
            return False
        return value

    @field_validator("allowed_origins")
    @classmethod
    def include_production_frontend(cls, value: list[str]) -> list[str]:
        production_origin = "https://sjssupermarket.vercel.app"
        return value if production_origin in value else [production_origin, *value]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
