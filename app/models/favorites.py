from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.responses import AnalyzeResponse

FavoriteSource = Literal["analyze", "classic", "invention"]


class FavoriteCreate(BaseModel):
    source: FavoriteSource = "analyze"
    slug: str | None = None
    payload: AnalyzeResponse


class FavoriteSummary(BaseModel):
    id: int
    source: FavoriteSource
    slug: str | None
    drink_name: str
    created_at: datetime
