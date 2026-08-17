from pathlib import Path

from app.models.buy_list import BuyList, BuyListGroup, BuyListItem
from app.models.recipe import Ingredient, IngredientCategory, Recipe
from app.services.buy_list import build_buy_list
from app.services.paneco_sales import (
    EMPTY_INDEX,
    PROMOTIONS_PATH,
    SaleIndex,
    SaleProduct,
    apply_sales,
    build_index,
    families_in,
    parse_sale_products,
)

FIXTURE = Path(__file__).parent / "fixtures" / "paneco_sale_page.html"


class TestParseSaleProducts:
    """Parsed against real markup captured from a Paneco listing page."""

    def test_reads_name_and_both_prices(self):
        products = parse_sale_products(FIXTURE.read_text(encoding="utf-8"))
        assert products
        for product in products:
            assert product.name
            assert product.url.startswith("http")
            assert product.sale_price < product.price

    def test_ignores_products_without_a_discount(self):
        html = """
        <li class="product-item">
          <a class="product-item-link" href="https://x/full-price">Full price gin</a>
          <span data-price-type="finalPrice" data-price-amount="99"></span>
        </li>
        <li class="product-item">
          <a class="product-item-link" href="https://x/discounted">Cheap gin</a>
          <span data-price-type="finalPrice" data-price-amount="99"></span>
          <span data-price-type="registerPrice" data-price-amount="79"></span>
        </li>
        """
        assert [p.name for p in parse_sale_products(html)] == ["Cheap gin"]

    def test_ignores_a_member_price_that_is_not_lower(self):
        html = """
        <li class="product-item">
          <a class="product-item-link" href="https://x/same">Same price</a>
          <span data-price-type="finalPrice" data-price-amount="99"></span>
          <span data-price-type="registerPrice" data-price-amount="99"></span>
        </li>
        """
        assert parse_sale_products(html) == []

    def test_handles_attributes_in_either_order(self):
        html = """
        <li class="product-item">
          <a class="product-item-link" href="https://x/a">Reversed</a>
          <span data-price-amount="120" data-price-type="finalPrice"></span>
          <span data-price-amount="90" data-price-type="registerPrice"></span>
        </li>
        """
        assert parse_sale_products(html)[0].sale_price == 90

    def test_empty_page(self):
        assert parse_sale_products("<html><body>nothing here</body></html>") == []

    def test_skips_miniatures(self):
        html = """
        <li class="product-item">
          <a class="product-item-link" href="https://x/mini">גיבסון פינק -ג'ין ורוד -מיניאטורה</a>
          <span data-price-type="finalPrice" data-price-amount="15"></span>
          <span data-price-type="registerPrice" data-price-amount="10.9"></span>
        </li>
        """
        # Cheapest discount in the catalogue and useless advice for a cocktail.
        assert parse_sale_products(html) == []


def product(name: str, price: float, sale: float, url: str | None = None) -> SaleProduct:
    return SaleProduct(name=name, url=url or f"https://x/{abs(hash(name))}", price=price, sale_price=sale)


class TestBuildIndex:
    """Attribution is the part that can quietly lie, so it is pinned down here."""

    def test_dedicated_category_needs_no_name_match(self):
        # "גורדונס" never says "gin"; being on /gin is the evidence.
        index = build_index({"/gin": [product("גורדונס - ליטר", 99, 88.9)]}, [])
        assert index.for_ingredient("London dry gin").product_name == "גורדונס - ליטר"

    def test_shared_liqueur_shelf_requires_the_product_to_name_itself(self):
        shelf = [
            product("פיזנג אמבון - ליקר בננות", 79, 59),
            product("קמפרי - ליטר כשר", 84.9, 74.9),
        ]
        index = build_index({"/liqueur": shelf}, [])
        # Campari gets Campari...
        assert index.for_ingredient("Campari").product_name == "קמפרי - ליטר כשר"
        # ...and sweet vermouth gets nothing, rather than inheriting the banana
        # liqueur just because they share a page.
        assert index.for_ingredient("sweet vermouth") is None

    def test_promotions_only_count_when_the_name_matches(self):
        promoted = [product("טנקרי ג'ין יבש - ליטר", 159, 144.9), product("שוקולד", 30, 20)]
        index = build_index({PROMOTIONS_PATH: promoted}, promoted)
        gin = index.for_ingredient("gin")
        assert gin.product_name == "טנקרי ג'ין יבש - ליטר"
        assert index.for_ingredient("vodka") is None

    def test_best_discount_wins_not_lowest_price(self):
        index = build_index(
            {
                "/gin": [
                    product("cheap small gin", 100, 90),   # 10% off
                    product("pricier gin", 400, 240),      # 40% off
                ]
            },
            [],
        )
        best = index.for_ingredient("gin")
        assert best.product_name == "pricier gin"
        assert best.discount_percent == 40
        assert best.also_on_sale == 1

    def test_a_product_in_both_places_is_counted_once(self):
        gin = product("טנקרי ג'ין יבש", 159, 144.9, url="https://x/tanq")
        index = build_index({"/gin": [gin], PROMOTIONS_PATH: [gin]}, [gin])
        assert index.for_ingredient("gin").also_on_sale == 0

    def test_mezcal_shares_the_tequila_page_and_must_name_itself(self):
        index = build_index({"/tequila": [product("דון חוליו אנייחו", 399, 299)]}, [])
        assert index.for_ingredient("blanco tequila") is not None
        assert index.for_ingredient("mezcal") is None


def gin_index() -> SaleIndex:
    return SaleIndex(
        {
            "gin": [
                SaleProduct(name="גורדונס - ליטר", url="https://x/1", price=99, sale_price=88.9),
                SaleProduct(name="בולדוג - ליטר", url="https://x/2", price=149, sale_price=129),
            ]
        }
    )


def gin_and_lime() -> Recipe:
    return Recipe(
        drink_name="Test",
        summary="x",
        is_alcoholic=True,
        glassware="coupe",
        ingredients=[
            Ingredient(name="London dry gin", amount=2, unit="oz", category=IngredientCategory.SPIRIT),
            Ingredient(name="lime", amount=1, unit="piece", category=IngredientCategory.PRODUCE),
        ],
        steps=["Serve."],
    )


class TestApplySales:
    def test_badges_the_deepest_discount_and_counts_the_rest(self):
        # Gordon's is cheaper in absolute terms (₪88.90) but only 10% off;
        # Bulldog is the actual deal at 13%.
        buy_list = apply_sales(build_buy_list(gin_and_lime()), gin_index())
        gin = buy_list.groups[0].items[0]
        assert gin.sale.product_name == "בולדוג - ליטר"
        assert gin.sale.sale_price == 129
        assert gin.sale.discount_percent == 13
        assert gin.sale.also_on_sale == 1

    def test_matches_by_family_not_by_exact_name(self):
        # "London dry gin" is not a key in the index; its family is.
        assert apply_sales(build_buy_list(gin_and_lime()), gin_index()).groups[0].items[0].sale

    def test_leaves_unlinked_items_alone(self):
        buy_list = apply_sales(build_buy_list(gin_and_lime()), gin_index())
        lime = next(i for g in buy_list.groups for i in g.items if i.ingredient_name == "lime")
        assert lime.paneco_url is None
        assert lime.sale is None

    def test_no_index_means_no_badges_not_a_claim_of_full_price(self):
        buy_list = apply_sales(build_buy_list(gin_and_lime()), EMPTY_INDEX)
        assert all(i.sale is None for g in buy_list.groups for i in g.items)

    def test_family_with_no_discounts_gets_nothing(self):
        buy_list = apply_sales(build_buy_list(gin_and_lime()), SaleIndex({"rum": []}))
        assert buy_list.groups[0].items[0].sale is None


class TestFamiliesIn:
    def test_only_families_we_can_link(self):
        assert families_in(build_buy_list(gin_and_lime())) == {"gin"}

    def test_empty_buy_list(self):
        assert families_in(BuyList(groups=[])) == set()

    def test_ignores_items_without_a_link(self):
        buy_list = BuyList(
            groups=[
                BuyListGroup(
                    category=IngredientCategory.PRODUCE,
                    label="Produce",
                    items=[BuyListItem(ingredient_name="lime", category=IngredientCategory.PRODUCE,
                                       suggested_purchase="Fresh lime")],
                )
            ]
        )
        assert families_in(buy_list) == set()
