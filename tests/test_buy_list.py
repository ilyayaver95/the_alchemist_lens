from app.models.recipe import Ingredient, IngredientCategory, Recipe
from app.services.buy_list import (
    apply_staple_flags,
    build_buy_list,
    is_pantry_staple,
    normalize_name,
)


def make_recipe(ingredients: list[Ingredient]) -> Recipe:
    return Recipe(
        drink_name="Test Drink",
        summary="A test drink.",
        is_alcoholic=True,
        glassware="rocks glass",
        ingredients=ingredients,
        steps=["Combine and serve."],
    )


class TestNormalizeName:
    def test_strips_descriptors(self):
        assert normalize_name("Crushed Ice") == "ice"
        assert normalize_name("freshly squeezed lime juice") == "lime juice"
        assert normalize_name("granulated white sugar") == "sugar"
        assert normalize_name("hot water") == "water"

    def test_all_descriptor_name_falls_back(self):
        assert normalize_name("Fresh") == "fresh"


class TestStapleDetection:
    def test_staples(self):
        for name in ["ice", "Crushed ice", "hot water", "sugar", "kosher salt", "honey"]:
            assert is_pantry_staple(name), name

    def test_non_staples(self):
        for name in ["mezcal", "simple syrup", "lime juice", "club soda", "agave syrup"]:
            assert not is_pantry_staple(name), name

    def test_apply_staple_flags_overrides_llm(self):
        recipe = make_recipe(
            [
                Ingredient(name="crushed ice", is_pantry_staple=False),
                Ingredient(name="mezcal", is_pantry_staple=True, category=IngredientCategory.SPIRIT),
            ]
        )
        apply_staple_flags(recipe)
        assert recipe.ingredients[0].is_pantry_staple is True
        assert recipe.ingredients[1].is_pantry_staple is False


class TestBuildBuyList:
    def test_staples_go_to_assumed_not_groups(self):
        recipe = make_recipe(
            [
                Ingredient(name="crushed ice", category=IngredientCategory.PANTRY),
                Ingredient(name="gin", amount=2, unit="oz", category=IngredientCategory.SPIRIT),
            ]
        )
        buy_list = build_buy_list(recipe)
        assert buy_list.staples_assumed == ["crushed ice"]
        all_names = [i.ingredient_name for g in buy_list.groups for i in g.items]
        assert all_names == ["gin"]

    def test_spirit_bottle_and_servings(self):
        recipe = make_recipe(
            [Ingredient(name="mezcal", amount=2, unit="oz", category=IngredientCategory.SPIRIT)]
        )
        item = build_buy_list(recipe).groups[0].items[0]
        assert item.suggested_purchase == "750 ml bottle of mezcal"
        # 750 ml / (2 oz * 29.57 ml) = 12.68 -> 12
        assert item.est_servings == "~12 drinks per bottle"

    def test_no_servings_without_amount_or_for_produce(self):
        recipe = make_recipe(
            [
                Ingredient(name="gin", category=IngredientCategory.SPIRIT),
                Ingredient(name="lime", amount=1, unit="piece", category=IngredientCategory.PRODUCE),
            ]
        )
        items = [i for g in build_buy_list(recipe).groups for i in g.items]
        assert all(i.est_servings is None for i in items)

    def test_simple_syrup_suggests_making_at_home(self):
        recipe = make_recipe(
            [Ingredient(name="simple syrup", amount=0.5, unit="oz", category=IngredientCategory.SYRUP)]
        )
        item = build_buy_list(recipe).groups[0].items[0]
        assert "Make at home" in item.suggested_purchase

    def test_deduplicates_by_normalized_name(self):
        recipe = make_recipe(
            [
                Ingredient(name="lime juice", amount=1, unit="oz", category=IngredientCategory.JUICE),
                Ingredient(name="Fresh lime juice", amount=0.5, unit="oz", category=IngredientCategory.JUICE),
            ]
        )
        items = [i for g in build_buy_list(recipe).groups for i in g.items]
        assert len(items) == 1

    def test_groups_follow_display_order(self):
        recipe = make_recipe(
            [
                Ingredient(name="mint", category=IngredientCategory.GARNISH),
                Ingredient(name="club soda", category=IngredientCategory.MIXER),
                Ingredient(name="white rum", amount=2, unit="oz", category=IngredientCategory.SPIRIT),
            ]
        )
        labels = [g.label for g in build_buy_list(recipe).groups]
        assert labels == ["Spirits", "Mixers & Sodas", "Garnishes"]

    def test_category_package_suggestions(self):
        cases = {
            IngredientCategory.LIQUEUR: ("orange liqueur", "750 ml bottle"),
            IngredientCategory.MIXER: ("tonic water", "1 L bottle"),
            IngredientCategory.JUICE: ("pineapple juice", "1 L bottle"),
            IngredientCategory.BEER: ("lager", "6-pack"),
            IngredientCategory.DAIRY: ("heavy cream", "Small carton"),
        }
        for category, (name, expected_prefix) in cases.items():
            recipe = make_recipe([Ingredient(name=name, category=category)])
            item = build_buy_list(recipe).groups[0].items[0]
            assert item.suggested_purchase.startswith(expected_prefix), item.suggested_purchase
