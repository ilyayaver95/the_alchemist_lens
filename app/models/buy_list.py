from pydantic import BaseModel, Field

from app.models.recipe import IngredientCategory


class PanecoSale(BaseModel):
    """A discount we have actually seen on Paneco.

    Only ever populated from a product observed with a member price below its
    list price. Absence means "we didn't find one", never "it isn't on sale" —
    we only read a slice of their catalogue, so the negative isn't ours to claim.
    """

    product_name: str
    price: float = Field(description="List price, in ILS")
    sale_price: float = Field(description="Discounted price, in ILS")
    url: str | None = None
    also_on_sale: int = Field(
        default=0, description="How many further discounted bottles of this kind we saw"
    )

    @property
    def discount_percent(self) -> int:
        return round((1 - self.sale_price / self.price) * 100) if self.price else 0


class BuyListItem(BaseModel):
    ingredient_name: str
    category: IngredientCategory
    suggested_purchase: str = Field(description="Realistic product to buy, e.g. '750 ml bottle of blanco tequila'")
    est_servings: str | None = Field(default=None, description="e.g. '~16 drinks per bottle'")
    paneco_query: str | None = Field(
        default=None, description="Search term used on Paneco; null when Paneco won't stock it"
    )
    paneco_url: str | None = Field(default=None, description="Deep link to that Paneco search")
    sale: PanecoSale | None = Field(
        default=None, description="A discount seen on Paneco for this kind of bottle"
    )


class BuyListGroup(BaseModel):
    category: IngredientCategory
    label: str
    items: list[BuyListItem]


class BuyList(BaseModel):
    groups: list[BuyListGroup]
    staples_assumed: list[str] = Field(
        default_factory=list, description="Pantry staples the recipe uses that you likely already have"
    )
    paneco_sale_url: str | None = Field(
        default=None, description="Paneco's current promotions page, for browsing what's discounted"
    )
