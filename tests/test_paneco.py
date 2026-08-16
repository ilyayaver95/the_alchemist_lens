from urllib.parse import parse_qs, urlparse

from app.models.recipe import Ingredient, IngredientCategory, Recipe
from app.services.buy_list import build_buy_list
from app.services.paneco import link_for, sale_url, search_term, search_url

BASE = "https://www.paneco.co.il"


def query_of(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


class TestSearchTerm:
    def test_maps_families_to_store_vocabulary(self):
        assert search_term("London dry gin") == "ג'ין"
        assert search_term("bourbon") == "וויסקי"
        assert search_term("aged rum") == "רום"
        assert search_term("Cointreau") == "טריפל סק"

    def test_unknown_ingredient_falls_back_to_its_own_name(self):
        assert search_term("Fernet Branca") == "fernet branca"


class TestSearchUrl:
    def test_points_at_the_magento_search_endpoint(self):
        url = search_url("campari", BASE)
        assert url.startswith(f"{BASE}/catalogsearch/result/?")
        assert query_of(url)["q"] == ["campari"]

    def test_sorts_cheapest_first_so_discounts_surface(self):
        params = query_of(search_url("campari", BASE))
        assert params["product_list_order"] == ["price"]
        assert params["product_list_dir"] == ["asc"]

    def test_hebrew_terms_are_percent_encoded(self):
        url = search_url("ג'ין", BASE)
        assert "%D7%92%27%D7%99%D7%9F" in url
        assert query_of(url)["q"] == ["ג'ין"]

    def test_trailing_slash_in_base_url_does_not_double_up(self):
        assert "//catalogsearch" not in search_url("gin", BASE + "/")

    def test_sale_url(self):
        assert sale_url(BASE) == f"{BASE}/special-offers"


class TestLinkFor:
    def test_links_drinkable_categories(self):
        for category in (
            IngredientCategory.SPIRIT,
            IngredientCategory.LIQUEUR,
            IngredientCategory.WINE,
            IngredientCategory.BEER,
            IngredientCategory.MIXER,
        ):
            assert link_for("gin", category, BASE) is not None, category

    def test_skips_what_a_liquor_store_does_not_sell(self):
        for name, category in [
            ("lime", IngredientCategory.PRODUCE),
            ("orange peel", IngredientCategory.GARNISH),
            ("heavy cream", IngredientCategory.DAIRY),
            ("ice", IngredientCategory.PANTRY),
            ("egg white", IngredientCategory.OTHER),
        ]:
            assert link_for(name, category, BASE) is None, name

    def test_links_bitters_despite_the_other_category(self):
        link = link_for("Angostura bitters", IngredientCategory.OTHER, BASE)
        assert link is not None
        assert link[0] == "angostura"


class TestBuyListIntegration:
    def test_buy_list_carries_links_and_the_sale_page(self):
        recipe = Recipe(
            drink_name="Test",
            summary="x",
            is_alcoholic=True,
            glassware="rocks glass",
            ingredients=[
                Ingredient(name="gin", amount=2, unit="oz", category=IngredientCategory.SPIRIT),
                Ingredient(name="lime", amount=1, unit="piece", category=IngredientCategory.PRODUCE),
            ],
            steps=["Serve."],
        )
        items = {i.ingredient_name: i for g in build_buy_list(recipe).groups for i in g.items}
        assert items["gin"].paneco_url and items["gin"].paneco_query == "ג'ין"
        assert items["lime"].paneco_url is None
        assert build_buy_list(recipe).paneco_sale_url == f"{BASE}/special-offers"

    def test_no_sale_link_when_nothing_is_buyable_there(self):
        recipe = Recipe(
            drink_name="Test",
            summary="x",
            is_alcoholic=False,
            glassware="highball",
            ingredients=[
                Ingredient(name="lime", amount=1, unit="piece", category=IngredientCategory.PRODUCE)
            ],
            steps=["Serve."],
        )
        assert build_buy_list(recipe).paneco_sale_url is None

    def test_base_url_is_configurable(self):
        recipe = Recipe(
            drink_name="Test",
            summary="x",
            is_alcoholic=True,
            glassware="coupe",
            ingredients=[Ingredient(name="gin", amount=2, unit="oz", category=IngredientCategory.SPIRIT)],
            steps=["Serve."],
        )
        buy_list = build_buy_list(recipe, "https://example.test")
        assert buy_list.groups[0].items[0].paneco_url.startswith("https://example.test/")
