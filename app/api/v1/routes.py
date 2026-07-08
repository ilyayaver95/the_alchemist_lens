from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile

from app.config import Settings, get_settings
from app.models.responses import AnalyzeResponse, HealthResponse
from app.services.recipe_service import InvalidImageError, RecipeService
from app.services.vision.base import (
    ProviderNotConfiguredError,
    RateLimitError,
    VisionProvider,
    VisionProviderError,
)
from app.services.vision.factory import get_provider

router = APIRouter()

_ACCEPTED_TYPES = {"image/jpeg", "image/png", "image/webp"}


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
    if image.content_type not in _ACCEPTED_TYPES:
        raise HTTPException(415, detail="Please upload a JPEG, PNG, or WebP image.")
    raw = await image.read()
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(413, detail="Image is too large (max 10 MB).")

    try:
        return await service.analyze(raw, drink_name=name.strip(), description=description.strip())
    except InvalidImageError:
        raise HTTPException(422, detail="That file doesn't look like a valid image.")
    except RateLimitError:
        raise HTTPException(
            429, detail="The free AI quota is momentarily exhausted — wait a minute and try again."
        )
    except VisionProviderError as exc:
        raise HTTPException(502, detail=f"The AI provider failed: {exc}")
