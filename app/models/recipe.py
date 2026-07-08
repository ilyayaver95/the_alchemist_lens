from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class IngredientCategory(str, Enum):
    SPIRIT = "spirit"
    LIQUEUR = "liqueur"
    WINE = "wine"
    BEER = "beer"
    MIXER = "mixer"
    JUICE = "juice"
    SYRUP = "syrup"
    PRODUCE = "produce"
    DAIRY = "dairy"
    GARNISH = "garnish"
    PANTRY = "pantry"
    OTHER = "other"


class Ingredient(BaseModel):
    name: str = Field(description="Ingredient name, e.g. 'blanco tequila'")
    amount: float | None = Field(default=None, description="Numeric quantity, null if to taste")
    unit: str | None = Field(default=None, description="oz, ml, dash, barspoon, piece, leaf, etc.")
    category: IngredientCategory = IngredientCategory.OTHER
    is_pantry_staple: bool = Field(default=False, description="True for ice, water, sugar, salt, etc.")
    notes: str | None = Field(default=None, description="e.g. 'freshly squeezed', 'chilled'")


class Recipe(BaseModel):
    drink_name: str
    summary: str = Field(description="One or two sentences describing the drink")
    is_alcoholic: bool
    estimated_abv: float | None = Field(
        default=None, ge=0, le=100, description="Estimated ABV percent of the finished drink, null if non-alcoholic"
    )
    method: Literal["shaken", "stirred", "built", "layered", "blended", "muddled", "brewed", "other"] = "other"
    glassware: str = Field(description="e.g. 'coupe', 'rocks glass', 'highball'")
    garnish: str | None = None
    ingredients: list[Ingredient]
    steps: list[str] = Field(description="Ordered preparation steps")
    visual_cues: list[str] = Field(
        default_factory=list,
        description="What in the photo informed the recipe: color, layering, garnish, glass shape",
    )
    confidence: Literal["low", "medium", "high"] = "medium"
