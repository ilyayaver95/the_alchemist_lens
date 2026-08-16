from app.services.ingredients import family_of
from app.services.pantry import MAX_MISSING, match_classics


def names(matches) -> list[str]:
    return [m.drink_name for m in matches]


class TestFamilyOf:
    def test_exact_names(self):
        assert family_of("Cointreau") == "triple sec"
        assert family_of("bourbon") == "whiskey"

    def test_brand_prefixed_names_from_a_shelf_photo(self):
        assert family_of("Tanqueray gin") == "gin"
        assert family_of("Hendrick's gin 700ml") == "gin"
        assert family_of("Grey Goose vodka") == "vodka"
        assert family_of("Martini Rosso sweet vermouth") == "sweet vermouth"

    def test_word_boundaries_keep_ginger_beer_from_becoming_gin(self):
        assert family_of("ginger beer") == "ginger beer"
        assert family_of("Fever-Tree ginger beer") == "ginger beer"

    def test_longer_phrases_win_over_shorter_ones(self):
        # "grapefruit soda" must not collapse to "grapefruit".
        assert family_of("Jarritos grapefruit soda") == "grapefruit soda"

    def test_unknown_names_pass_through_normalized(self):
        assert family_of("Fernet Branca") == "fernet branca"


class TestMakeable:
    def test_exact_shelf_makes_the_drink(self):
        makeable, _ = match_classics(["gin", "Campari", "sweet vermouth"])
        assert "Negroni" in names(makeable)

    def test_aliases_satisfy_the_recipe(self):
        # Cointreau covers "triple sec", bourbon covers "whiskey", and a lime
        # covers "lime juice".
        makeable, _ = match_classics(["blanco tequila", "Cointreau", "lime", "agave syrup"])
        assert "Margarita" in names(makeable)

    def test_staples_are_assumed_not_required(self):
        # Caipirinha needs cachaça, lime, and sugar — sugar is a staple.
        makeable, _ = match_classics(["cachaça", "limes"])
        assert "Caipirinha" in names(makeable)

    def test_garnishes_do_not_block_a_drink(self):
        # No orange peel on the shelf, but a Negroni is still makeable.
        makeable, _ = match_classics(["gin", "Campari", "sweet vermouth"])
        negroni = next(m for m in makeable if m.drink_name == "Negroni")
        assert "orange peel" not in negroni.missing

    def test_a_scanned_shelf_matches_by_brand(self):
        # Exactly what FakeProvider's shelf photo returns.
        makeable, _ = match_classics(
            ["Tanqueray gin", "Campari", "sweet vermouth", "tonic water", "lime"]
        )
        assert {"Negroni", "Gin & Tonic"} <= set(names(makeable))

    def test_optional_ingredients_do_not_block_a_drink(self):
        # Whiskey Sour lists egg white as optional.
        makeable, _ = match_classics(["bourbon", "lemon juice", "simple syrup", "angostura bitters"])
        assert "Whiskey Sour" in names(makeable)


class TestNearly:
    def test_reports_what_is_missing(self):
        _, nearly = match_classics(["gin", "Campari"])
        negroni = next(m for m in nearly if m.drink_name == "Negroni")
        assert negroni.missing == ["sweet vermouth"]
        assert sorted(negroni.have) == ["Campari", "gin"]

    def test_sorted_by_fewest_missing_first(self):
        _, nearly = match_classics(["gin", "Campari", "lemon juice"])
        counts = [len(m.missing) for m in nearly]
        assert counts == sorted(counts)

    def test_never_more_than_the_cap(self):
        _, nearly = match_classics(["gin"])
        assert all(len(m.missing) <= MAX_MISSING for m in nearly)

    def test_needs_at_least_one_bottle_you_own(self):
        # An empty-ish shelf shouldn't advertise drinks you have nothing for.
        _, nearly = match_classics(["banana"])
        assert nearly == []

    def test_a_makeable_drink_is_not_also_listed_as_nearly(self):
        makeable, nearly = match_classics(["gin", "Campari", "sweet vermouth"])
        assert set(names(makeable)).isdisjoint(names(nearly))


def test_blank_entries_are_ignored():
    assert match_classics(["  ", ""]) == ([], [])
