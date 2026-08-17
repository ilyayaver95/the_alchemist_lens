"""Which bottles are currently discounted on Paneco.

This is the one place in the app that reads Paneco rather than just linking to
it, and it is deliberately narrow:

- Only category landing pages and the promotions page are fetched. Both are
  plain paths; their robots.txt disallows `/catalogsearch/` and every
  query-string URL, so nothing here paginates, sorts, or searches.
- The origin rejects non-browser clients, so the request carries browser
  headers. That is a deliberate choice, made explicitly.
- The whole catalogue slice is fetched once and cached on disk for hours. A
  buy list must never cost Paneco a request per ingredient.
- Every failure is soft. No sale data simply means no badges; the buy list, the
  links and the recipe are unaffected.

We only ever make the positive claim. No badge means we did not find a discount
in the slice we read — not that the bottle is full price. And a badge only
appears when we can attribute the product to that ingredient: several families
share the liqueur category, so Campari must not inherit a discount on banana
liqueur just because they sit on the same page.
"""

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.models.buy_list import BuyList, PanecoSale
from app.services.ingredients import family_of

logger = logging.getLogger(__name__)

# Ingredient family -> Paneco category path. Plain paths only, no query strings.
CATEGORY_PATHS: dict[str, str] = {
    "gin": "/gin",
    "vodka": "/vodka",
    "rum": "/rum",
    "whiskey": "/whiskey",
    "tequila": "/tequila",
    "mezcal": "/tequila",
    "cachaça": "/cachaca",
    "sparkling wine": "/champagne",
    "triple sec": "/liqueur",
    "coffee liqueur": "/liqueur",
    "campari": "/liqueur",
    "aperol": "/liqueur",
    "sweet vermouth": "/liqueur",
    "dry vermouth": "/liqueur",
    "aromatic bitters": "/liqueur",
    "orange bitters": "/liqueur",
}

# Families whose category page contains only that kind of bottle, so anything
# discounted on it is a genuine match. Everything else has to name itself.
DEDICATED_CATEGORIES = {
    "gin",
    "vodka",
    "rum",
    "whiskey",
    "tequila",
    "cachaça",
    "sparkling wine",
}

# Substrings that identify a product as belonging to a family. Used to attribute
# promotions-page finds, and as the *only* evidence for families that share the
# liqueur shelf. Hebrew first, since that is how the catalogue is written.
NAME_HINTS: dict[str, tuple[str, ...]] = {
    "gin": ("ג'ין", "ג׳ין", "gin"),
    "vodka": ("וודקה", "vodka"),
    "rum": ("רום", "rum"),
    "whiskey": ("וויסקי", "ויסקי", "whisky", "whiskey"),
    "tequila": ("טקילה", "tequila"),
    "mezcal": ("מסקל", "mezcal"),
    "cachaça": ("קשאסה", "cachaca"),
    "sparkling wine": ("פרוסקו", "שמפניה", "prosecco", "champagne"),
    "triple sec": ("קואנטרו", "טריפל סק", "cointreau", "curacao"),
    "coffee liqueur": ("קלואה", "kahlua", "תיה מריה"),
    "campari": ("קמפרי", "campari"),
    "aperol": ("אפרול", "aperol"),
    "sweet vermouth": ("ורמוט", "vermouth"),
    "dry vermouth": ("ורמוט", "vermouth"),
    "aromatic bitters": ("אנגוסטורה", "angostura"),
    "orange bitters": ("ביטר", "bitters"),
}

# A 50 ml miniature is technically the cheapest discount and useless advice.
_EXCLUDED_NAME_PARTS = ("מיניאטורה", "miniature")

PROMOTIONS_PATH = "/special-offers"

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
}

_ITEM_SPLIT = re.compile(r'(?=<li[^>]*class="[^"]*product-item)')
_NAME = re.compile(r'class="product-item-link"[^>]*href="([^"]*)"[^>]*>\s*(.*?)\s*</a>', re.S)
_TAGS = re.compile(r"<[^>]+>")


def _price(block: str, kind: str) -> float | None:
    """Magento emits the amount and the type as attributes in either order."""
    for pattern in (
        rf'data-price-amount="([\d.]+)"[^>]*data-price-type="{kind}"',
        rf'data-price-type="{kind}"[^>]*data-price-amount="([\d.]+)"',
    ):
        if match := re.search(pattern, block):
            try:
                return float(match.group(1))
            except ValueError:
                return None
    return None


@dataclass(frozen=True)
class SaleProduct:
    name: str
    url: str
    price: float
    sale_price: float

    @property
    def discount(self) -> float:
        return 1 - self.sale_price / self.price if self.price else 0.0


def parse_sale_products(html: str) -> list[SaleProduct]:
    """Products on a listing page whose member price beats their list price."""
    products: list[SaleProduct] = []
    for block in _ITEM_SPLIT.split(html)[1:]:
        name_match = _NAME.search(block)
        if not name_match:
            continue
        url, raw_name = name_match.groups()
        name = re.sub(r"\s+", " ", _TAGS.sub("", raw_name)).strip()
        price = _price(block, "finalPrice")
        sale_price = _price(block, "registerPrice")
        if not name or price is None or sale_price is None or sale_price >= price:
            continue
        if any(part in name for part in _EXCLUDED_NAME_PARTS):
            continue
        products.append(SaleProduct(name=name, url=url, price=price, sale_price=sale_price))
    return products


def names_family(family: str, product_name: str) -> bool:
    return any(hint in product_name for hint in NAME_HINTS.get(family, ()))


class SaleIndex:
    """Discounted products, keyed by the ingredient family they belong to."""

    def __init__(self, by_family: dict[str, list[SaleProduct]]) -> None:
        self._by_family = by_family

    def __bool__(self) -> bool:
        return any(self._by_family.values())

    def for_ingredient(self, ingredient_name: str) -> PanecoSale | None:
        products = self._by_family.get(family_of(ingredient_name))
        if not products:
            return None
        # Best discount, not lowest price: the badge exists to say "there is a
        # real deal on this", and the cheapest bottle is usually just the
        # smallest one.
        best = max(products, key=lambda p: p.discount)
        return PanecoSale(
            product_name=best.name,
            price=best.price,
            sale_price=best.sale_price,
            url=best.url,
            also_on_sale=len(products) - 1,
        )

    def to_json(self) -> dict:
        return {
            family: [
                {"name": p.name, "url": p.url, "price": p.price, "sale_price": p.sale_price}
                for p in products
            ]
            for family, products in self._by_family.items()
        }

    @classmethod
    def from_json(cls, data: dict) -> "SaleIndex":
        return cls({f: [SaleProduct(**p) for p in items] for f, items in data.items()})


EMPTY_INDEX = SaleIndex({})


def build_index(
    by_path: dict[str, list[SaleProduct]], promoted: list[SaleProduct]
) -> SaleIndex:
    """Attribute discounted products to families. Pure, so it can be tested."""
    by_family: dict[str, list[SaleProduct]] = {}
    for family, path in CATEGORY_PATHS.items():
        candidates = list(by_path.get(path, []))
        # Promotions span every category, so those only count when the product
        # names itself.
        candidates += [p for p in promoted if names_family(family, p.name)]

        # For a dedicated category, sitting on that page is proof enough. Where
        # families share a shelf — everything on /liqueur — the product has to
        # name itself, or Campari inherits a discount on banana liqueur.
        matched = (
            candidates
            if family in DEDICATED_CATEGORIES
            else [p for p in candidates if names_family(family, p.name)]
        )

        # De-duplicate by URL: a bottle can appear in both places.
        unique: dict[str, SaleProduct] = {p.url: p for p in matched}
        by_family[family] = list(unique.values())
    return SaleIndex(by_family)


def apply_sales(buy_list: BuyList, index: SaleIndex) -> BuyList:
    """Attach sale hints to the items we have a Paneco link for. Pure."""
    for group in buy_list.groups:
        for item in group.items:
            if item.paneco_url:
                item.sale = index.for_ingredient(item.ingredient_name)
    return buy_list


def families_in(buy_list: BuyList) -> set[str]:
    """The ingredient families a buy list could show a badge for."""
    return {
        family_of(item.ingredient_name)
        for group in buy_list.groups
        for item in group.items
        if item.paneco_url
    }


class SaleIndexCache:
    """Disk-backed cache so a buy list never triggers a fetch per ingredient."""

    def __init__(self, cache_dir: str, ttl_hours: float) -> None:
        self._path = Path(cache_dir) / "paneco-sales.json"
        self._ttl_seconds = ttl_hours * 3600

    def read(self) -> SaleIndex | None:
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if time.time() - payload.get("fetched_at", 0) > self._ttl_seconds:
            return None
        return SaleIndex.from_json(payload.get("families", {}))

    def write(self, index: SaleIndex) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps({"fetched_at": time.time(), "families": index.to_json()}),
                encoding="utf-8",
            )
        except OSError:
            logger.warning("Could not write the Paneco sale cache", exc_info=True)


async def _fetch(client: httpx.AsyncClient, url: str) -> list[SaleProduct]:
    response = await client.get(url)
    response.raise_for_status()
    return parse_sale_products(response.text)


async def fetch_sale_index(base_url: str) -> SaleIndex:
    """Read the promotions page and every category we know how to use.

    Always the full set, never just the families in the buy list at hand — a
    partial index would be cached and then answer "no discount" for every drink
    that came later.
    """
    base = base_url.rstrip("/")
    paths = [PROMOTIONS_PATH, *dict.fromkeys(CATEGORY_PATHS.values())]

    async with httpx.AsyncClient(
        headers=_BROWSER_HEADERS, timeout=httpx.Timeout(20.0, connect=10.0), follow_redirects=True
    ) as client:
        # Concurrently: this runs on the first buy list after the cache expires,
        # and a dozen sequential page loads would be felt.
        results = await asyncio.gather(
            *(_fetch(client, f"{base}{path}") for path in paths), return_exceptions=True
        )

    by_path: dict[str, list[SaleProduct]] = {}
    for path, result in zip(paths, results, strict=True):
        if isinstance(result, BaseException):
            logger.info("Paneco page %s unavailable: %s", path, result)
            by_path[path] = []
        else:
            by_path[path] = result

    return build_index(by_path, by_path.get(PROMOTIONS_PATH, []))


async def decorate_with_sales(buy_list: BuyList, settings) -> BuyList:
    """Badge the buy list with any discounts we can confirm.

    Cache first, network only on a miss, and any failure leaves the buy list
    exactly as it was.
    """
    if not settings.paneco_sales_enabled or not families_in(buy_list):
        return buy_list

    cache = SaleIndexCache(settings.cache_dir, settings.paneco_sales_ttl_hours)
    index = cache.read()
    if index is None:
        try:
            index = await fetch_sale_index(settings.paneco_base_url)
        except Exception:  # noqa: BLE001 — a shopping badge must never break a recipe
            logger.warning("Could not read Paneco sales", exc_info=True)
            return buy_list
        # Written even when empty: individual pages already fail soft, and
        # caching the disappointment is what stops every request retrying.
        cache.write(index)

    return apply_sales(buy_list, index)
