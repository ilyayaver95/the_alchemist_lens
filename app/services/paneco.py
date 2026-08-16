"""Deep links from a buy list into Paneco (paneco.co.il).

Link generation only — we never fetch Paneco from the server. Their robots.txt
disallows `/catalogsearch/` and every query-string URL, and the origin 403s
non-browser clients, so the search runs in the user's own browser when they tap
a link. That also means this module can't break when their HTML changes.

Verified against the live site (Magento 2):
  - search:      /catalogsearch/result/?q=<term>
  - sort params: &product_list_order=price&product_list_dir=asc
  - sale page:   /special-offers
  - the index matches both English brand terms ("cointreau") and the store's own
    Hebrew category words ("ג'ין"), which is why the table below mixes the two.
"""

from urllib.parse import urlencode

from app.models.recipe import IngredientCategory
from app.services.ingredients import family_of, normalize_name

SEARCH_PATH = "/catalogsearch/result/"
SALE_PATH = "/special-offers"

# Categories Paneco actually stocks. Limes and egg whites get no link.
_LINKABLE_CATEGORIES = {
    IngredientCategory.SPIRIT,
    IngredientCategory.LIQUEUR,
    IngredientCategory.WINE,
    IngredientCategory.BEER,
    IngredientCategory.MIXER,
}

# Bitters are miscategorised as "other" by both the LLM and the library, but
# Paneco sells them, so link them anyway.
_ALWAYS_LINK_FAMILIES = {"aromatic bitters", "orange bitters"}

# Ingredient family -> the term that gives the best result set on Paneco.
# Hebrew where it is the store's own category word, English for brand names.
_SEARCH_TERMS = {
    "gin": "ג'ין",
    "vodka": "וודקה",
    "rum": "רום",
    "whiskey": "וויסקי",
    "tequila": "טקילה",
    "mezcal": "mezcal",
    "cachaça": "cachaca",
    "triple sec": "טריפל סק",
    "sweet vermouth": "sweet vermouth",
    "dry vermouth": "dry vermouth",
    "campari": "campari",
    "aperol": "aperol",
    "sparkling wine": "prosecco",
    "coffee liqueur": "kahlua",
    "tonic water": "טוניק",
    "soda water": "סודה",
    "ginger beer": "ginger beer",
    "aromatic bitters": "angostura",
    "orange bitters": "orange bitters",
}


def search_term(ingredient_name: str) -> str:
    """Best Paneco search term for an ingredient, falling back to its own name."""
    family = family_of(ingredient_name)
    return _SEARCH_TERMS.get(family, normalize_name(ingredient_name))


def search_url(term: str, base_url: str, cheapest_first: bool = True) -> str:
    """Deep link to a Paneco search, cheapest first so discounts surface early."""
    params = {"q": term}
    if cheapest_first:
        params["product_list_order"] = "price"
        params["product_list_dir"] = "asc"
    return f"{base_url.rstrip('/')}{SEARCH_PATH}?{urlencode(params)}"


def sale_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}{SALE_PATH}"


def link_for(
    ingredient_name: str, category: IngredientCategory, base_url: str
) -> tuple[str, str] | None:
    """`(term, url)` for a buyable drink ingredient, or None if Paneco won't have it."""
    linkable = category in _LINKABLE_CATEGORIES or family_of(ingredient_name) in _ALWAYS_LINK_FAMILIES
    if not linkable:
        return None
    term = search_term(ingredient_name)
    return term, search_url(term, base_url)
