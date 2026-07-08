from pydantic import BaseModel, Field

from app.models.recipe import IngredientCategory


class BuyListItem(BaseModel):
    ingredient_name: str
    category: IngredientCategory
    suggested_purchase: str = Field(description="Realistic product to buy, e.g. '750 ml bottle of blanco tequila'")
    est_servings: str | None = Field(default=None, description="e.g. '~16 drinks per bottle'")


class BuyListGroup(BaseModel):
    category: IngredientCategory
    label: str
    items: list[BuyListItem]


class BuyList(BaseModel):
    groups: list[BuyListGroup]
    staples_assumed: list[str] = Field(
        default_factory=list, description="Pantry staples the recipe uses that you likely already have"
    )
