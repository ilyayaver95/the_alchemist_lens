from functools import lru_cache

from app.config import Settings, get_settings
from app.services.vision.base import ProviderNotConfiguredError, VisionProvider
from app.services.vision.fake import FakeProvider
from app.services.vision.gemini import GeminiProvider
from app.services.vision.ollama import OllamaProvider


def build_provider(settings: Settings) -> VisionProvider:
    match settings.vision_provider:
        case "gemini":
            if not settings.gemini_api_key:
                raise ProviderNotConfiguredError(
                    "GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com "
                    "and put it in .env (see .env.example)."
                )
            return GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
        case "ollama":
            return OllamaProvider(base_url=settings.ollama_base_url, model=settings.ollama_model)
        case "fake":
            return FakeProvider()
    raise ProviderNotConfiguredError(f"Unknown provider: {settings.vision_provider}")


@lru_cache
def get_provider() -> VisionProvider:
    return build_provider(get_settings())
