import asyncio
import hashlib
import io
import json
import logging
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.config import Settings
from app.models.responses import AnalyzeResponse
from app.services.buy_list import apply_staple_flags, build_buy_list
from app.services.vision.base import RateLimitError, VisionProvider, VisionProviderError

logger = logging.getLogger(__name__)

_RETRY_DELAYS_SECONDS = (2.0, 5.0)


class InvalidImageError(Exception):
    """Uploaded file is not a decodable image."""


def prepare_image(image_bytes: bytes, max_dimension: int) -> tuple[bytes, str]:
    """Decode, downscale, and re-encode as JPEG to keep token usage low."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError("Could not decode the uploaded image") from exc

    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    if max(image.size) > max_dimension:
        image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    out = io.BytesIO()
    image.save(out, format="JPEG", quality=85)
    return out.getvalue(), "image/jpeg"


class RecipeService:
    def __init__(self, provider: VisionProvider, settings: Settings) -> None:
        self._provider = provider
        self._settings = settings
        self._cache_dir = Path(settings.cache_dir)

    def _cache_path(self, image_bytes: bytes, drink_name: str, description: str) -> Path:
        digest = hashlib.sha256()
        digest.update(f"{self._provider.name}|{self._provider.model}|".encode())
        digest.update(f"{drink_name.strip().lower()}|{description.strip().lower()}|".encode())
        digest.update(image_bytes)
        return self._cache_dir / f"{digest.hexdigest()}.json"

    def _read_cache(self, path: Path) -> AnalyzeResponse | None:
        if not self._settings.cache_enabled or not path.exists():
            return None
        try:
            response = AnalyzeResponse.model_validate_json(path.read_text())
        except (ValueError, OSError):
            return None
        response.cached = True
        return response

    def _write_cache(self, path: Path, response: AnalyzeResponse) -> None:
        if not self._settings.cache_enabled:
            return
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(response.model_dump_json())
        except OSError:
            logger.warning("Failed to write response cache at %s", path, exc_info=True)

    async def _analyze_with_retry(
        self, image_bytes: bytes, mime_type: str, drink_name: str, description: str
    ):
        for delay in _RETRY_DELAYS_SECONDS:
            try:
                return await self._provider.analyze(image_bytes, mime_type, drink_name, description)
            except RateLimitError:
                logger.info("Rate limited by %s, retrying in %.0fs", self._provider.name, delay)
                await asyncio.sleep(delay)
        return await self._provider.analyze(image_bytes, mime_type, drink_name, description)

    async def analyze(self, raw_image: bytes, drink_name: str, description: str) -> AnalyzeResponse:
        image_bytes, mime_type = prepare_image(raw_image, self._settings.max_image_dimension)

        cache_path = self._cache_path(image_bytes, drink_name, description)
        if cached := self._read_cache(cache_path):
            logger.info("Cache hit for '%s'", drink_name)
            return cached

        recipe = await self._analyze_with_retry(image_bytes, mime_type, drink_name, description)
        recipe = apply_staple_flags(recipe)
        response = AnalyzeResponse(
            recipe=recipe,
            buy_list=build_buy_list(recipe),
            provider=self._provider.name,
            model=self._provider.model,
            cached=False,
        )
        self._write_cache(cache_path, response)
        return response


__all__ = ["InvalidImageError", "RecipeService", "VisionProviderError", "prepare_image"]
