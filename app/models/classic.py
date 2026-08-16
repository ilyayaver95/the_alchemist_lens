from pydantic import BaseModel, Field

from app.models.recipe import Recipe


class ClassicCocktail(BaseModel):
    """A hand-written recipe from the bundled library.

    The payload is a plain `Recipe` — the same shape the LLM produces — so every
    downstream consumer (buy list, Paneco links, the frontend renderer) works on
    library drinks without a single branch.
    """

    slug: str = Field(description="URL-safe id, e.g. 'old-fashioned'")
    tags: list[str] = Field(default_factory=list, description="Base spirit, method, mood")
    recipe: Recipe


class ClassicSummary(BaseModel):
    """Lightweight projection for the browse grid — no ingredients or steps."""

    slug: str
    drink_name: str
    summary: str
    tags: list[str]
    glassware: str
    estimated_abv: float | None = None

    @classmethod
    def of(cls, classic: ClassicCocktail) -> "ClassicSummary":
        return cls(
            slug=classic.slug,
            drink_name=classic.recipe.drink_name,
            summary=classic.recipe.summary,
            tags=classic.tags,
            glassware=classic.recipe.glassware,
            estimated_abv=classic.recipe.estimated_abv,
        )
