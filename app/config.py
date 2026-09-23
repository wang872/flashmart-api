from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FlashMart"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 120
    database_url: str = "sqlite:///./data/flashmart.db"
    payment_webhook_secret: str = "flashmart-webhook-secret"
    cache_ttl_seconds: int = 60
    algorithm: str = "HS256"
    seed_on_startup: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
