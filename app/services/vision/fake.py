"""In-memory provider for tests and offline demos — never calls a network."""

from app.models.recipe import Ingredient, IngredientCategory, Recipe
from app.services.vision.base import VisionProvider

SAMPLE_RECIPE = Recipe(
    drink_name="Smoky Margarita",
    summary="A mezcal-forward twist on the classic margarita with a chili-salt rim.",
    is_alcoholic=True,
    estimated_abv=18.0,
    method="shaken",
    glassware="rocks glass",
    garnish="lime wheel and chili salt rim",
    ingredients=[
        Ingredient(name="mezcal", amount=2.0, unit="oz", category=IngredientCategory.SPIRIT),
        Ingredient(name="orange liqueur", amount=0.75, unit="oz", category=IngredientCategory.LIQUEUR),
        Ingredient(name="lime juice", amount=1.0, unit="oz", category=IngredientCategory.JUICE,
                   notes="freshly squeezed"),
        Ingredient(name="agave syrup", amount=0.5, unit="oz", category=IngredientCategory.SYRUP),
        Ingredient(name="crushed ice", category=IngredientCategory.PANTRY),
        Ingredient(name="lime", amount=1.0, unit="piece", category=IngredientCategory.GARNISH),
    ],
    steps=[
        "Rim a chilled rocks glass with chili salt.",
        "Shake mezcal, orange liqueur, lime juice, and agave syrup with ice for 12 seconds.",
        "Strain over fresh ice into the rimmed glass.",
        "Garnish with a lime wheel.",
    ],
    visual_cues=["pale cloudy color suggests citrus", "red-flecked rim", "rocks glass with large cube"],
    confidence="high",
)


class FakeProvider(VisionProvider):
    name = "fake"
    model = "canned-response"

    async def analyze(
        self, image_bytes: bytes, mime_type: str, drink_name: str, description: str
    ) -> Recipe:
        recipe = SAMPLE_RECIPE.model_copy(deep=True)
        recipe.drink_name = drink_name or recipe.drink_name
        return recipe
