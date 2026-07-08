from abc import ABC, abstractmethod

from app.models.recipe import Recipe


class VisionProviderError(Exception):
    """The provider failed to produce a usable recipe."""


class RateLimitError(VisionProviderError):
    """The provider is rate-limiting us (e.g. free-tier quota)."""


class ProviderNotConfiguredError(VisionProviderError):
    """The selected provider is missing configuration (e.g. API key)."""


class VisionProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def analyze(
        self, image_bytes: bytes, mime_type: str, drink_name: str, description: str
    ) -> Recipe: ...
