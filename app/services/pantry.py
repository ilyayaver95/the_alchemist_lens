"""Match a home bar against the classic library.

Pure Python, like the buy list: no LLM call is needed to tell you that gin,
Campari, and sweet vermouth make a Negroni.
"""

from app.models.pantry import ClassicMatch
from app.models.recipe import Ingredient, IngredientCategory
from app.services.classics import list_classics
from app.services.ingredients import family_of, is_pantry_staple

# How many bottles short a drink can be and still be worth showing.
MAX_MISSING = 2


def _is_required(ingredient: Ingredient) -> bool:
    """Whether a missing bottle would actually stop you making the drink.

    Staples are assumed present, garnishes are cosmetic, and anything the recipe
    itself calls optional is exactly that — counting them would leave almost
    nothing "makeable".
    """
    if is_pantry_staple(ingredient.name):
        return False
    if ingredient.category is IngredientCategory.GARNISH:
        return False
    if ingredient.notes and "optional" in ingredient.notes.lower():
        return False
    return True


def match_classics(inventory: list[str]) -> tuple[list[ClassicMatch], list[ClassicMatch]]:
    """Split the library into what you can make now and what you're 1–2 short of."""
    owned = {family_of(item) for item in inventory if item.strip()}

    makeable: list[ClassicMatch] = []
    nearly: list[ClassicMatch] = []

    for classic in list_classics():
        required: dict[str, str] = {}
        for ingredient in classic.recipe.ingredients:
            if _is_required(ingredient):
                required.setdefault(family_of(ingredient.name), ingredient.name)
        if not required:
            continue

        have = [name for family, name in required.items() if family in owned]
        missing = [name for family, name in required.items() if family not in owned]

        match = ClassicMatch(
            slug=classic.slug,
            drink_name=classic.recipe.drink_name,
            summary=classic.recipe.summary,
            glassware=classic.recipe.glassware,
            have=have,
            missing=missing,
        )
        if not missing:
            makeable.append(match)
        elif len(missing) <= MAX_MISSING and have:
            # `have` must be non-empty: "you're two bottles away" is only useful
            # advice when you already own something the drink needs.
            nearly.append(match)

    makeable.sort(key=lambda m: m.drink_name.lower())
    nearly.sort(key=lambda m: (len(m.missing), -len(m.have), m.drink_name.lower()))
    return makeable, nearly
