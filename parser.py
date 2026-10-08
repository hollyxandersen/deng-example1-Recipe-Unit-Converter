import pandas as pd

KNOWN_UNITS = {
    "g", "gram", "grams",
    "ml", "mls","millilitre", "millilitres",
    "cup", "cups",
    "tbsp","tbsps", "tablespoon", "tablespoons",
    "tsp","tsps", "teaspoon", "teaspoons"
}

UNIT_MAP = {
    "g": "g",
    "gram": "g",
    "grams": "g",

    "ml": "ml",
    "mls": "ml",
    "millilitre": "ml",
    "millilitres": "ml",

    "cup": "cups",
    "cups": "cups",

    "tbsp": "tbsp",
    "tbsps": "tbsp",
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",

    "tsp": "tsp",
    "tsps": "tsp",
    "teaspoon": "tsp",
    "teaspoons": "tsp"
}


def parse_recipe_line(line):
    line = line.strip()

    if not line:
        return None

    parts = line.split()

    # For now, only handle lines starting with a simple numeric quantity
    try:
        quantity = float(parts[0])
    except ValueError:
        return {
            "quantity": None,
            "unit": None,
            "ingredient": line,
            "type": "text",
            "original_text": line
        }

    # Check whether the second item is a recognised measurement unit
    if len(parts) > 1 and parts[1].lower() in KNOWN_UNITS:
        unit = UNIT_MAP[parts[1].lower()]
        ingredient = " ".join(parts[2:])

        return {
            "quantity": quantity,
            "unit": unit,
            "ingredient": ingredient,
            "type": "measurable",
            "original_text": line
        }

    # Numeric quantity, but no recognised measurement unit
    ingredient = " ".join(parts[1:])

    return {
        "quantity": quantity,
        "unit": None,
        "ingredient": ingredient,
        "type": "count",
        "original_text": line
    }


def parse_recipe_text(recipe_text):
    rows = []

    for line in recipe_text.splitlines():
        parsed = parse_recipe_line(line)

        if parsed is not None:
            rows.append(parsed)

    return pd.DataFrame(rows)


recipe_text = """
2 cups plain flour
1 tbsp brown sugar
250 ml milk
1 onion
2 cloves garlic
salt to taste
"""

