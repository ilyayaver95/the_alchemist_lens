"""Orchestrates the home-bar screen: read a shelf photo, then suggest drinks."""

import logging

from app.config import Settings
from app.models.pantry import PantryResponse, PantryScan
from app.models.responses import AnalyzeResponse
from app.services.buy_list import apply_staple_flags, build_buy_list
from app.services.llm_retry import with_rate_limit_retry
from app.services.pantry import match_classics
from app.services.recipe_service import prepare_image
from app.services.vision.base import (
    ProviderNotConfiguredError,
    VisionProvider,
    VisionProviderError,
)

logger = logging.getLogger(__name__)

_NO_PROVIDER = (
    "No AI provider is configured, so shelf photos can't be read. "
    "Type your bottles in instead, or set GEMINI_API_KEY."
)


class PantryService:
    def __init__(self, provider: VisionProvider | None, settings: Settings) -> None:
        # The provider is optional: matching classics is pure Python, and only
        # the photo scan and the invention actually need a model.
        self._provider = provider
        self._settings = settings

    async def scan(self, raw_image: bytes, hint: str) -> PantryScan:
        if self._provider is None:
            raise ProviderNotConfiguredError(_NO_PROVIDER)
        provider = self._provider
        image_bytes, mime_type = prepare_image(raw_image, self._settings.max_image_dimension)
        return await with_rate_limit_retry(
            lambda: provider.identify_bottles(image_bytes, mime_type, hint),
            provider.name,
        )

    async def suggest(self, items: list[str], invent: bool) -> PantryResponse:
        inventory = [item.strip() for item in items if item.strip()]
        makeable, nearly = match_classics(inventory)

        invention: AnalyzeResponse | None = None
        if invent and self._settings.enable_invention and self._provider is not None:
            invention = await self._invent(inventory)

        return PantryResponse(
            inventory=inventory, makeable=makeable, nearly=nearly, invention=invention
        )

    async def _invent(self, inventory: list[str]) -> AnalyzeResponse | None:
        """An original is a bonus, not the point — a failure here must not sink
        the deterministic matches the user actually asked for."""
        provider = self._provider
        assert provider is not None  # guarded by the caller
        try:
            recipe = await with_rate_limit_retry(
                lambda: provider.invent_recipe(inventory), provider.name
            )
        except VisionProviderError:
            logger.warning("Invention failed via %s", self._provider.name, exc_info=True)
            return None

        recipe = apply_staple_flags(recipe)
        return AnalyzeResponse(
            recipe=recipe,
            buy_list=build_buy_list(recipe, self._settings.paneco_base_url),
            provider=provider.name,
            model=provider.model,
        )
