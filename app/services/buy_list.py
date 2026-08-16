"""Deterministic buy-list construction from a structured recipe.

The LLM only extracts ingredients; everything here is pure Python so it can be
unit-tested without any API access.
"""

from app.models.buy_list import BuyList, BuyListGroup, BuyListItem
from app.models.recipe import Ingredient, IngredientCategory, Recipe
from app.services import paneco
from app.services.ingredients import is_pantry_staple, normalize_name

# Kept in sync with Settings.paneco_base_url; callers that have settings should
# pass theirs, so the retailer stays configurable without threading config into
# this otherwise dependency-free module.
_DEFAULT_PANECO_BASE_URL = "https://www.paneco.co.il"

# Approximate volume of one unit, in ml, for serving estimates.
_UNIT_ML = {
    "ml": 1.0,
    "milliliter": 1.0,
    "milliliters": 1.0,
    "cl": 10.0,
    "oz": 29.57,
    "ounce": 29.57,
    "ounces": 29.57,
    "fl oz": 29.57,
    "shot": 44.0,
    "jigger": 44.0,
    "dash": 0.92,
    "dashes": 0.92,
    "barspoon": 5.0,
    "tsp": 4.93,
    "teaspoon": 4.93,
    "tbsp": 14.79,
    "tablespoon": 14.79,
    "cup": 236.6,
}

_BOTTLE_ML = {
    IngredientCategory.SPIRIT: 750,
    IngredientCategory.LIQUEUR: 750,
    IngredientCategory.WINE: 750,
    IngredientCategory.SYRUP: 375,
    IngredientCategory.MIXER: 1000,
    IngredientCategory.JUICE: 1000,
}

_GROUP_LABELS = {
    IngredientCategory.SPIRIT: "Spirits",
    IngredientCategory.LIQUEUR: "Liqueurs",
    IngredientCategory.WINE: "Wine",
    IngredientCategory.BEER: "Beer",
    IngredientCategory.MIXER: "Mixers & Sodas",
    IngredientCategory.JUICE: "Juices",
    IngredientCategory.SYRUP: "Syrups & Sweeteners",
    IngredientCategory.PRODUCE: "Produce",
    IngredientCategory.DAIRY: "Dairy",
    IngredientCategory.GARNISH: "Garnishes",
    IngredientCategory.PANTRY: "Pantry",
    IngredientCategory.OTHER: "Other",
}

# Display order of groups in the buy list.
_GROUP_ORDER = [
    IngredientCategory.SPIRIT,
    IngredientCategory.LIQUEUR,
    IngredientCategory.WINE,
    IngredientCategory.BEER,
    IngredientCategory.MIXER,
    IngredientCategory.JUICE,
    IngredientCategory.SYRUP,
    IngredientCategory.PRODUCE,
    IngredientCategory.DAIRY,
    IngredientCategory.GARNISH,
    IngredientCategory.PANTRY,
    IngredientCategory.OTHER,
]


def apply_staple_flags(recipe: Recipe) -> Recipe:
    """Override the LLM's staple guesses with our deterministic list."""
    for ingredient in recipe.ingredients:
        ingredient.is_pantry_staple = is_pantry_staple(ingredient.name)
    return recipe


def _estimate_servings(ingredient: Ingredient) -> str | None:
    bottle_ml = _BOTTLE_ML.get(ingredient.category)
    if bottle_ml is None or ingredient.amount is None or not ingredient.unit:
        return None
    per_drink_ml = _UNIT_ML.get(ingredient.unit.lower().strip())
    if per_drink_ml is None or ingredient.amount <= 0:
        return None
    servings = int(bottle_ml // (ingredient.amount * per_drink_ml))
    if servings < 1:
        return None
    return f"~{servings} drinks per bottle"


def _suggested_purchase(ingredient: Ingredient) -> str:
    name = ingredient.name
    normalized = normalize_name(name)
    if normalized == "simple syrup":
        return "Make at home (equal parts sugar and hot water) — or buy a 375 ml bottle"
    match ingredient.category:
        case IngredientCategory.SPIRIT | IngredientCategory.WINE:
            return f"750 ml bottle of {name}"
        case IngredientCategory.LIQUEUR:
            return f"750 ml bottle of {name} (375 ml if available)"
        case IngredientCategory.BEER:
            return f"6-pack of {name}"
        case IngredientCategory.MIXER:
            return f"1 L bottle of {name}"
        case IngredientCategory.JUICE:
            return f"1 L bottle of {name} — or fresh fruit to squeeze"
        case IngredientCategory.SYRUP:
            return f"375 ml bottle of {name}"
        case IngredientCategory.PRODUCE:
            return f"Fresh {name} (2–3 pieces)"
        case IngredientCategory.DAIRY:
            return f"Small carton of {name}"
        case IngredientCategory.GARNISH:
            return f"Fresh {name} (small pack, or 1–2 pieces)"
        case _:
            return f"Small bottle or pack of {name}"


def build_buy_list(recipe: Recipe, paneco_base_url: str = _DEFAULT_PANECO_BASE_URL) -> BuyList:
    staples: list[str] = []
    by_category: dict[IngredientCategory, list[BuyListItem]] = {}
    seen: set[str] = set()

    for ingredient in recipe.ingredients:
        normalized = normalize_name(ingredient.name)
        if normalized in seen:
            continue
        seen.add(normalized)

        if is_pantry_staple(ingredient.name):
            staples.append(ingredient.name)
            continue

        link = paneco.link_for(ingredient.name, ingredient.category, paneco_base_url)
        item = BuyListItem(
            ingredient_name=ingredient.name,
            category=ingredient.category,
            suggested_purchase=_suggested_purchase(ingredient),
            est_servings=_estimate_servings(ingredient),
            paneco_query=link[0] if link else None,
            paneco_url=link[1] if link else None,
        )
        by_category.setdefault(ingredient.category, []).append(item)

    groups = [
        BuyListGroup(category=category, label=_GROUP_LABELS[category], items=by_category[category])
        for category in _GROUP_ORDER
        if category in by_category
    ]
    has_links = any(item.paneco_url for group in groups for item in group.items)
    return BuyList(
        groups=groups,
        staples_assumed=staples,
        paneco_sale_url=paneco.sale_url(paneco_base_url) if has_links else None,
    )
