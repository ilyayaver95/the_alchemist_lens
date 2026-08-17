from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile

from app.config import Settings, get_settings
from app.models.classic import ClassicSummary
from app.models.pantry import PantryResponse, PantryScan, PantrySuggestRequest
from app.models.responses import AnalyzeResponse, HealthResponse
from app.services.buy_list import build_buy_list
from app.services.classics import get_classic, list_classics
from app.services.paneco_sales import decorate_with_sales
from app.services.pantry_service import PantryService
from app.services.recipe_service import InvalidImageError, RecipeService
from app.services.vision.base import (
    ProviderNotConfiguredError,
    RateLimitError,
    UnsupportedCapabilityError,
    VisionProvider,
    VisionProviderError,
)
from app.services.vision.factory import get_provider

router = APIRouter()

_ACCEPTED_TYPES = {"image/jpeg", "image/png", "image/webp"}

CLASSICS_LIBRARY_VERSION = "classics-v1"


def get_vision_provider() -> VisionProvider:
    try:
        return get_provider()
    except ProviderNotConfiguredError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


def get_recipe_service(
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[VisionProvider, Depends(get_vision_provider)],
) -> RecipeService:
    return RecipeService(provider=provider, settings=settings)


def get_optional_vision_provider() -> VisionProvider | None:
    """Like get_vision_provider, but tolerates a missing API key.

    Matching a home bar against the classics is pure Python — it must keep
    working on an instance that has no AI provider configured at all.
    """
    try:
        return get_provider()
    except ProviderNotConfiguredError:
        return None


def get_pantry_service(
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[VisionProvider | None, Depends(get_optional_vision_provider)],
) -> PantryService:
    return PantryService(provider=provider, settings=settings)


async def read_image_upload(image: UploadFile, settings: Settings) -> bytes:
    """Shared upload guard so /analyze and /pantry/scan can't drift apart."""
    if image.content_type not in _ACCEPTED_TYPES:
        raise HTTPException(415, detail="Please upload a JPEG, PNG, or WebP image.")
    raw = await image.read()
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(413, detail="Image is too large (max 10 MB).")
    return raw


def _provider_http_error(exc: VisionProviderError) -> HTTPException:
    if isinstance(exc, ProviderNotConfiguredError):
        return HTTPException(503, detail=str(exc))
    if isinstance(exc, RateLimitError):
        return HTTPException(
            429, detail="The free AI quota is momentarily exhausted — wait a minute and try again."
        )
    if isinstance(exc, UnsupportedCapabilityError):
        return HTTPException(501, detail=f"This feature needs a different AI provider: {exc}")
    return HTTPException(502, detail=f"The AI provider failed: {exc}")


@router.get("/health", response_model=HealthResponse)
async def health(provider: Annotated[VisionProvider, Depends(get_vision_provider)]) -> HealthResponse:
    return HealthResponse(status="ok", provider=provider.name, model=provider.model)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    image: UploadFile,
    name: Annotated[str, Form(min_length=1, max_length=200)],
    service: Annotated[RecipeService, Depends(get_recipe_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    description: Annotated[str, Form(max_length=2000)] = "",
) -> AnalyzeResponse:
    raw = await read_image_upload(image, settings)
    try:
        return await service.analyze(raw, drink_name=name.strip(), description=description.strip())
    except InvalidImageError:
        raise HTTPException(422, detail="That file doesn't look like a valid image.")
    except VisionProviderError as exc:
        raise _provider_http_error(exc) from exc


@router.get("/classics", response_model=list[ClassicSummary])
async def classics() -> list[ClassicSummary]:
    return [ClassicSummary.of(classic) for classic in list_classics()]


@router.get("/classics/{slug}", response_model=AnalyzeResponse)
async def classic_detail(
    slug: str, settings: Annotated[Settings, Depends(get_settings)]
) -> AnalyzeResponse:
    classic = get_classic(slug)
    if classic is None:
        raise HTTPException(404, detail="No classic by that name — try the list.")
    # Shaped as an AnalyzeResponse so library drinks render, save, and link to
    # Paneco through exactly the same code as an analyzed photo.
    buy_list = await decorate_with_sales(
        build_buy_list(classic.recipe, settings.paneco_base_url), settings
    )
    return AnalyzeResponse(
        recipe=classic.recipe,
        buy_list=buy_list,
        provider="library",
        model=CLASSICS_LIBRARY_VERSION,
    )


@router.post("/pantry/scan", response_model=PantryScan)
async def pantry_scan(
    image: UploadFile,
    service: Annotated[PantryService, Depends(get_pantry_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    hint: Annotated[str, Form(max_length=500)] = "",
) -> PantryScan:
    raw = await read_image_upload(image, settings)
    try:
        return await service.scan(raw, hint=hint.strip())
    except InvalidImageError:
        raise HTTPException(422, detail="That file doesn't look like a valid image.")
    except VisionProviderError as exc:
        raise _provider_http_error(exc) from exc


@router.post("/pantry/suggest", response_model=PantryResponse)
async def pantry_suggest(
    body: PantrySuggestRequest,
    service: Annotated[PantryService, Depends(get_pantry_service)],
) -> PantryResponse:
    # No provider errors to map: matching is pure Python, and a failed invention
    # is downgraded to `invention: null` rather than sinking the whole response.
    return await service.suggest(items=body.items, invent=body.invent)
