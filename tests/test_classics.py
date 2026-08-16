from app.models.recipe import IngredientCategory
from app.services.buy_list import build_buy_list
from app.services.classics import get_classic, list_classics


def test_library_is_stocked():
    classics = list_classics()
    assert len(classics) >= 20


def test_slugs_are_unique_and_url_safe():
    slugs = [c.slug for c in list_classics()]
    assert len(set(slugs)) == len(slugs)
    for slug in slugs:
        assert slug == slug.lower()
        assert " " not in slug


def test_every_recipe_is_complete():
    for classic in list_classics():
        recipe = classic.recipe
        assert recipe.ingredients, classic.slug
        assert recipe.steps, classic.slug
        assert recipe.glassware, classic.slug
        assert recipe.summary, classic.slug
        # Every alcoholic classic should name at least one thing to pour.
        if recipe.is_alcoholic:
            assert recipe.estimated_abv is not None, classic.slug
            assert any(
                i.category in (IngredientCategory.SPIRIT, IngredientCategory.LIQUEUR, IngredientCategory.WINE)
                for i in recipe.ingredients
            ), classic.slug


def test_every_classic_builds_a_buy_list():
    for classic in list_classics():
        buy_list = build_buy_list(classic.recipe)
        assert buy_list.groups, classic.slug


def test_lookup_by_slug_is_case_insensitive():
    assert get_classic("NEGRONI").recipe.drink_name == "Negroni"
    assert get_classic("no-such-drink") is None
