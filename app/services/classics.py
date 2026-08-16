"""The bundled classic-cocktail library.

Hand-written recipes, no LLM involved: browsing classics costs nothing, works
offline, and always returns the same well-balanced proportions.
"""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import TypeAdapter

from app.models.classic import ClassicCocktail

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "classics.json"

_ADAPTER = TypeAdapter(list[ClassicCocktail])


@lru_cache
def load_classics() -> tuple[ClassicCocktail, ...]:
    """Parse and validate the bundled library once per process.

    A malformed entry raises at first use rather than surfacing as a broken
    response later, and duplicate slugs are caught here too.
    """
    classics = _ADAPTER.validate_python(json.loads(DATA_PATH.read_text(encoding="utf-8")))
    slugs = [c.slug for c in classics]
    if len(set(slugs)) != len(slugs):
        duplicates = sorted({s for s in slugs if slugs.count(s) > 1})
        raise ValueError(f"Duplicate slugs in {DATA_PATH.name}: {', '.join(duplicates)}")
    return tuple(classics)


def list_classics() -> list[ClassicCocktail]:
    return sorted(load_classics(), key=lambda c: c.recipe.drink_name.lower())


@lru_cache
def _by_slug() -> dict[str, ClassicCocktail]:
    return {c.slug: c for c in load_classics()}


def get_classic(slug: str) -> ClassicCocktail | None:
    return _by_slug().get(slug.strip().lower())
