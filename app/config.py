from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def get_settings() -> Settings:
    return Settings()
