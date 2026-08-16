"""Shared ingredient vocabulary: normalization, pantry staples, and families.

Extracted so the buy list, the Paneco linker, and the home-bar matcher all agree
on what "crushed ice" and "freshly squeezed lime juice" reduce to. Pure data and
pure functions — no I/O, no models beyond the ones it is handed.
"""

# Words that describe form/preparation, not identity: "crushed ice" -> "ice".
_DESCRIPTORS = {
    "fresh",
    "freshly",
    "squeezed",
    "crushed",
    "cubed",
    "cracked",
    "hot",
    "cold",
    "warm",
    "chilled",
    "granulated",
    "white",
    "filtered",
    "still",
    "fine",
    "coarse",
    "ground",
}

# Ingredients assumed to already be in the user's kitchen (matched after
# descriptor stripping, so "crushed ice" and "granulated sugar" count).
_PANTRY_STAPLES = {
    "ice",
    "water",
    "sugar",
    "brown sugar",
    "salt",
    "sea salt",
    "kosher salt",
    "celery salt",
    "honey",
    "black pepper",
    "pepper",
    "cinnamon",
    "nutmeg",
    "vanilla extract",
}

# Recipe line -> canonical family. Anything on the left satisfies anything else
# mapping to the same family, so a bottle of Cointreau on your shelf covers a
# recipe that asks for triple sec. Keys are already normalized.
_FAMILIES: dict[str, str] = {
    # whisky
    "bourbon": "whiskey",
    "rye": "whiskey",
    "rye whiskey": "whiskey",
    "whisky": "whiskey",
    "whiskey": "whiskey",
    "scotch": "whiskey",
    "scotch whisky": "whiskey",
    # rum
    "rum": "rum",
    "light rum": "rum",
    "aged rum": "rum",
    "dark rum": "rum",
    "gold rum": "rum",
    "jamaican rum": "rum",
    "spiced rum": "rum",
    # agave
    "tequila": "tequila",
    "blanco tequila": "tequila",
    "silver tequila": "tequila",
    "reposado tequila": "tequila",
    "mezcal": "mezcal",
    # gin / vodka
    "gin": "gin",
    "london dry gin": "gin",
    "dry gin": "gin",
    "vodka": "vodka",
    "citron vodka": "vodka",
    "citrus vodka": "vodka",
    # orange liqueur
    "cointreau": "triple sec",
    "triple sec": "triple sec",
    "orange liqueur": "triple sec",
    "orange curacao": "triple sec",
    "orange curaçao": "triple sec",
    "curacao": "triple sec",
    "grand marnier": "triple sec",
    # vermouth & aperitivo
    "sweet vermouth": "sweet vermouth",
    "red vermouth": "sweet vermouth",
    "rosso vermouth": "sweet vermouth",
    "dry vermouth": "dry vermouth",
    "campari": "campari",
    "aperol": "aperol",
    # sparkling
    "prosecco": "sparkling wine",
    "champagne": "sparkling wine",
    "sparkling wine": "sparkling wine",
    "cava": "sparkling wine",
    # coffee
    "coffee liqueur": "coffee liqueur",
    "kahlua": "coffee liqueur",
    "kahlúa": "coffee liqueur",
    "tia maria": "coffee liqueur",
    "espresso": "espresso",
    "coffee": "espresso",
    # citrus: the fruit and its juice are the same shopping problem
    "lime": "lime",
    "lime juice": "lime",
    "limes": "lime",
    "lime wedge": "lime",
    "lime wheel": "lime",
    "lemon": "lemon",
    "lemon juice": "lemon",
    "lemons": "lemon",
    "lemon wedge": "lemon",
    "lemon wheel": "lemon",
    "lemon peel": "lemon",
    "lemon twist": "lemon",
    "orange": "orange",
    "orange juice": "orange",
    "orange peel": "orange",
    "orange slice": "orange",
    "orange twist": "orange",
    "grapefruit": "grapefruit",
    "grapefruit juice": "grapefruit",
    "grapefruit wedge": "grapefruit",
    # sweeteners
    "simple syrup": "simple syrup",
    "sugar syrup": "simple syrup",
    "gomme syrup": "simple syrup",
    "agave syrup": "agave syrup",
    "agave nectar": "agave syrup",
    "orgeat": "orgeat",
    "orgeat syrup": "orgeat",
    "almond syrup": "orgeat",
    # mixers
    "soda water": "soda water",
    "club soda": "soda water",
    "sparkling water": "soda water",
    "tonic": "tonic water",
    "tonic water": "tonic water",
    "ginger beer": "ginger beer",
    "grapefruit soda": "grapefruit soda",
    # bitters & sundries
    "bitters": "aromatic bitters",
    "angostura": "aromatic bitters",
    "angostura bitters": "aromatic bitters",
    "aromatic bitters": "aromatic bitters",
    "orange bitters": "orange bitters",
    "mint": "mint",
    "mint leaves": "mint",
    "mint sprig": "mint",
    "cachaca": "cachaça",
    "cachaça": "cachaça",
}


def normalize_name(name: str) -> str:
    words = name.lower().replace(",", " ").split()
    kept = [w for w in words if w not in _DESCRIPTORS]
    return " ".join(kept) if kept else name.lower().strip()


def is_pantry_staple(name: str) -> bool:
    return normalize_name(name) in _PANTRY_STAPLES


def family_of(name: str) -> str:
    """Canonical family for an ingredient, falling back to its normalized name.

    A shelf photo yields brand-first names — "Tanqueray gin", "Hendrick's gin
    700ml" — so when the whole name isn't a known family we look for the longest
    known phrase inside it. Matching on whole words is what keeps "ginger beer"
    from being read as gin.
    """
    normalized = normalize_name(name)
    if normalized in _FAMILIES:
        return _FAMILIES[normalized]

    words = normalized.split()
    for length in range(len(words) - 1, 0, -1):
        for start in range(len(words) - length + 1):
            candidate = " ".join(words[start : start + length])
            if candidate in _FAMILIES:
                return _FAMILIES[candidate]
    return normalized
