from pydantic import BaseModel, Field

from app.models.recipe import IngredientCategory
from app.models.responses import AnalyzeResponse


class PantryItem(BaseModel):
    name: str = Field(description="What the bottle is, e.g. 'Tanqueray gin' or 'lime'")
    category: IngredientCategory = IngredientCategory.OTHER


class PantryScan(BaseModel):
    """What the vision model saw on the shelf."""

    items: list[PantryItem] = Field(default_factory=list)
    notes: str | None = Field(
        default=None, description="Anything unreadable or ambiguous in the photo"
    )


class PantrySuggestRequest(BaseModel):
    items: list[str] = Field(min_length=1, max_length=80)
    invent: bool = Field(
        default=False, description="Also ask the model for one original built from these bottles"
    )


class ClassicMatch(BaseModel):
    slug: str
    drink_name: str
    summary: str
    glassware: str
    have: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)


class PantryResponse(BaseModel):
    inventory: list[str]
    makeable: list[ClassicMatch] = Field(default_factory=list)
    nearly: list[ClassicMatch] = Field(
        default_factory=list, description="One or two bottles short"
    )
    invention: AnalyzeResponse | None = None
