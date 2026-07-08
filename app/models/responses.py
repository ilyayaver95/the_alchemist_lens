from pydantic import BaseModel

from app.models.buy_list import BuyList
from app.models.recipe import Recipe


class AnalyzeResponse(BaseModel):
    recipe: Recipe
    buy_list: BuyList
    provider: str
    model: str
    cached: bool = False


class HealthResponse(BaseModel):
    status: str
    provider: str
    model: str
