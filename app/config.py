from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    vision_provider: Literal["gemini", "ollama", "fake"] = "gemini"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5vl:7b"

    cache_enabled: bool = True
    cache_dir: str = ".cache"

    max_upload_bytes: int = 10 * 1024 * 1024
    max_image_dimension: int = 1280

    # Accounts and favorites. SQLite locally, Postgres on Render.
    database_url: str = "sqlite:///./alchemist.db"
    jwt_secret: str = DEV_JWT_SECRET
    jwt_ttl_hours: int = 24 * 30
    # Must be true anywhere the app is served over HTTPS.
    cookie_secure: bool = False

    @model_validator(mode="after")
    def _reject_dev_secret_in_production(self) -> "Settings":
        # cookie_secure is only set where the app is served over HTTPS, which is
        # exactly where a guessable signing key would let anyone forge a session.
        if self.cookie_secure and self.jwt_secret == DEV_JWT_SECRET:
            raise ValueError("Set JWT_SECRET to a random value before deploying with COOKIE_SECURE=true.")
        return self

    # Retailer used for the "build bucket list" deep links.
    paneco_base_url: str = "https://www.paneco.co.il"

    # Read Paneco's category and promotions pages to badge discounted bottles.
    # Off turns the app back into a pure link builder that fetches nothing.
    paneco_sales_enabled: bool = True
    paneco_sales_ttl_hours: float = 12.0

    # Whether the home-bar screen may spend an LLM call inventing an original.
    enable_invention: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
