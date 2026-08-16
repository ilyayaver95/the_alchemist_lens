import io

import pytest
from PIL import Image

from app.config import Settings
from app.models.recipe import Recipe
from app.services.recipe_service import InvalidImageError, RecipeService, prepare_image
from app.services.vision.base import RateLimitError, VisionProvider
from app.services.vision.fake import SAMPLE_RECIPE


def make_image_bytes(width: int = 64, height: int = 64, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (200, 120, 40)).save(buf, format=fmt)
    return buf.getvalue()


class TestPrepareImage:
    def test_reencodes_as_jpeg(self):
        data, mime = prepare_image(make_image_bytes(), max_dimension=1280)
        assert mime == "image/jpeg"
        assert Image.open(io.BytesIO(data)).format == "JPEG"

    def test_downscales_large_images(self):
        data, _ = prepare_image(make_image_bytes(3000, 1500), max_dimension=1280)
        image = Image.open(io.BytesIO(data))
        assert max(image.size) == 1280

    def test_rejects_garbage(self):
        with pytest.raises(InvalidImageError):
            prepare_image(b"definitely not an image", max_dimension=1280)


class FlakyProvider(VisionProvider):
    name = "flaky"
    model = "test"

    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    async def analyze(self, image_bytes, mime_type, drink_name, description) -> Recipe:
        self.calls += 1
        if self.calls <= self.failures:
            raise RateLimitError("quota")
        return SAMPLE_RECIPE.model_copy(deep=True)


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        vision_provider="fake",
        cache_enabled=True,
        cache_dir=str(tmp_path / "cache"),
        _env_file=None,
    )


async def test_retries_on_rate_limit(settings, monkeypatch):
    monkeypatch.setattr("app.services.llm_retry._RETRY_DELAYS_SECONDS", (0, 0))
    provider = FlakyProvider(failures=2)
    service = RecipeService(provider=provider, settings=settings)
    response = await service.analyze(make_image_bytes(), "Margarita", "classic")
    assert provider.calls == 3
    assert response.recipe.drink_name == "Smoky Margarita"


async def test_rate_limit_surfaces_after_retries_exhausted(settings, monkeypatch):
    monkeypatch.setattr("app.services.llm_retry._RETRY_DELAYS_SECONDS", (0, 0))
    service = RecipeService(provider=FlakyProvider(failures=10), settings=settings)
    with pytest.raises(RateLimitError):
        await service.analyze(make_image_bytes(), "Margarita", "classic")


async def test_cache_hit_skips_provider(settings):
    provider = FlakyProvider(failures=0)
    service = RecipeService(provider=provider, settings=settings)
    first = await service.analyze(make_image_bytes(), "Margarita", "classic")
    second = await service.analyze(make_image_bytes(), "Margarita", "classic")
    assert provider.calls == 1
    assert first.cached is False
    assert second.cached is True


async def test_different_inputs_miss_cache(settings):
    provider = FlakyProvider(failures=0)
    service = RecipeService(provider=provider, settings=settings)
    await service.analyze(make_image_bytes(), "Margarita", "classic")
    await service.analyze(make_image_bytes(), "Paloma", "grapefruit")
    assert provider.calls == 2
