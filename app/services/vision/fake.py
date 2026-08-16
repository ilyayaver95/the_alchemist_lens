"""In-memory provider for tests and offline demos — never calls a network."""

from app.models.pantry import PantryItem, PantryScan
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


# A shelf that can actually make something from the classics library (Negroni,
# Gin & Tonic) so the offline demo isn't an empty result screen.
SAMPLE_SHELF = PantryScan(
    items=[
        PantryItem(name="Tanqueray gin", category=IngredientCategory.SPIRIT),
        PantryItem(name="Campari", category=IngredientCategory.LIQUEUR),
        PantryItem(name="sweet vermouth", category=IngredientCategory.WINE),
        PantryItem(name="tonic water", category=IngredientCategory.MIXER),
        PantryItem(name="lime", category=IngredientCategory.PRODUCE),
    ],
    notes="One bottle at the back was out of focus.",
)

SAMPLE_INVENTION = Recipe(
    drink_name="Alembic Sling",
    summary="A gin and Campari highball stretched with tonic and sharpened with lime.",
    is_alcoholic=True,
    estimated_abv=11.0,
    method="built",
    glassware="highball",
    garnish="lime wheel",
    ingredients=[
        Ingredient(name="gin", amount=1.5, unit="oz", category=IngredientCategory.SPIRIT),
        Ingredient(name="Campari", amount=0.5, unit="oz", category=IngredientCategory.LIQUEUR),
        Ingredient(name="lime juice", amount=0.5, unit="oz", category=IngredientCategory.JUICE),
        Ingredient(name="tonic water", amount=4.0, unit="oz", category=IngredientCategory.MIXER),
        Ingredient(name="ice", category=IngredientCategory.PANTRY),
    ],
    steps=[
        "Fill a highball glass with ice.",
        "Add gin, Campari, and lime juice.",
        "Top with tonic water and stir once.",
        "Garnish with a lime wheel.",
    ],
    visual_cues=[],
    confidence="medium",
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

    async def identify_bottles(self, image_bytes: bytes, mime_type: str, hint: str) -> PantryScan:
        return SAMPLE_SHELF.model_copy(deep=True)

    async def invent_recipe(self, inventory: list[str]) -> Recipe:
        return SAMPLE_INVENTION.model_copy(deep=True)
