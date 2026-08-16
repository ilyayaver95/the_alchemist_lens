from abc import ABC, abstractmethod

from app.models.pantry import PantryScan
from app.models.recipe import Recipe


class VisionProviderError(Exception):
    """The provider failed to produce a usable recipe."""


class RateLimitError(VisionProviderError):
    """The provider is rate-limiting us (e.g. free-tier quota)."""


class ProviderNotConfiguredError(VisionProviderError):
    """The selected provider is missing configuration (e.g. API key)."""


class UnsupportedCapabilityError(VisionProviderError):
    """The provider does not implement this call."""


class VisionProvider(ABC):
    name: str
    model: str

    @abstractmethod
    async def analyze(
        self, image_bytes: bytes, mime_type: str, drink_name: str, description: str
    ) -> Recipe: ...

    # The two calls below are concrete rather than abstract on purpose: analyze()
    # is the contract every provider must honour, while shelf scanning and recipe
    # invention are optional extras. A provider that skips them fails loudly at
    # the one endpoint that needs them instead of failing to instantiate at all.

    async def identify_bottles(self, image_bytes: bytes, mime_type: str, hint: str) -> PantryScan:
        raise UnsupportedCapabilityError(f"{self.name} cannot read a shelf photo")

    async def invent_recipe(self, inventory: list[str]) -> Recipe:
        raise UnsupportedCapabilityError(f"{self.name} cannot invent recipes")
