"""
RECIPE TEXT PARSER
------------------

Converts unstructured recipe ingredient lists into a
DataFrame containing quantities, units, ingredient names,
notes and row classifications.

Main functions
--------------
clean_recipe_line():
    Removes leading formatting characters.

split_ingredient_and_note():
    Separates ingredient names from comma-delimited notes.

remove_leading_of():
    Removes optional "of" following measurement units.

is_recipe_header():
    Identifies likely recipe section headings.

parse_quantity():
    Extracts quantities, fractions, ranges and attached units.

parse_recipe_line():
    Extracts ingredient details and classifies individual lines.

parse_recipe_text():
    Processes the complete recipe into a Pandas DataFrame.
"""



import pandas as pd
from fractions import Fraction
import re


# ---------------------------------------------------------
# SUPPORTED UNITS
# ---------------------------------------------------------

KNOWN_UNITS = {
    "g", "gram", "grams",
    "kg", "kilogram", "kilograms",
    "ml", "mls", "millilitre", "millilitres",
    "l", "litre", "litres",
    "cup", "cups",
    "tbsp", "tbsps", "tablespoon", "tablespoons",
    "tsp", "tsps", "teaspoon", "teaspoons",
}


UNIT_MAP = {
    "g": "g",
    "gram": "g",
    "grams": "g",

    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",

    "ml": "ml",
    "mls": "ml",
    "millilitre": "ml",
    "millilitres": "ml",

    "l": "l",
    "litre": "l",
    "litres": "l",

    "cup": "cup",
    "cups": "cup",

    "tbsp": "tbsp",
    "tbsps": "tbsp",
    "tablespoon": "tbsp",
    "tablespoons": "tbsp",

    "tsp": "tsp",
    "tsps": "tsp",
    "teaspoon": "tsp",
    "teaspoons": "tsp",
}


# ---------------------------------------------------------
# TEXT CLEANING
# ---------------------------------------------------------

def clean_recipe_line(line):
    """
    Remove leading bullets, checkboxes and other symbols
    from copied recipe text.
    """

    line = line.strip()

    line = re.sub(
        r"^[^A-Za-z0-9½⅓⅔¼¾⅛⅜⅝⅞]+",
        "",
        line
    )

    return line.strip()


def split_ingredient_and_note(ingredient):
    """
    Split ingredient text at the first comma.

    Example:
        "tapioca starch, or use potato starch"

    becomes:
        ingredient = "tapioca starch"
        note = "or use potato starch"
    """

    if "," in ingredient:
        main, note = ingredient.split(",", 1)

        return (
            main.strip(),
            note.strip()
        )

    return ingredient.strip(), None


def remove_leading_of(parts):
    """
    Remove a leading 'of' after a measurement unit.

    Example:
        ['of', 'plain', 'flour']
        -> ['plain', 'flour']
    """

    if parts and parts[0].lower() == "of":
        return parts[1:]

    return parts


def is_recipe_header(line):
    """
    Identify likely recipe section headings.
    """

    line_clean = line.strip()

    return (
        line_clean.lower().startswith("for the ")
        or line_clean.lower().startswith("for ")
        or (
            line_clean.isupper()
            and not any(char.isdigit() for char in line_clean)
        )
    )


# ---------------------------------------------------------
# QUANTITY PARSING
# ---------------------------------------------------------

def parse_quantity(parts):
    """
    Parse a quantity from the beginning of a recipe line.

    Returns:
        quantity
        quantity_min
        quantity_max
        consumed_parts
        attached_unit
    """

    if not parts:
        return None, None, None, 0, None

    first = parts[0]

    unicode_fractions = {
        "½": 0.5,
        "⅓": 1 / 3,
        "⅔": 2 / 3,
        "¼": 0.25,
        "¾": 0.75,
        "⅛": 0.125,
        "⅜": 0.375,
        "⅝": 0.625,
        "⅞": 0.875,
    }

    # Range with attached unit
    # e.g. 80-120g
    range_attached_match = re.fullmatch(
        r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)(kg|g|ml|l|tsp|tbsp|cup|cups)",
        first.lower()
    )

    if range_attached_match:
        quantity_min = float(range_attached_match.group(1))
        quantity_max = float(range_attached_match.group(2))
        raw_unit = range_attached_match.group(3)

        unit = UNIT_MAP.get(raw_unit, raw_unit)

        return None, quantity_min, quantity_max, 1, unit

    # Range with separate unit
    # e.g. 1-2 tbsp
    range_match = re.fullmatch(
        r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)",
        first
    )

    if range_match:
        quantity_min = float(range_match.group(1))
        quantity_max = float(range_match.group(2))

        return None, quantity_min, quantity_max, 1, None

    # Quantity with attached unit
    # e.g. 150g, 250ml
    attached_unit_match = re.fullmatch(
        r"(\d+(?:\.\d+)?)(kg|g|ml|l|tsp|tbsp|cup|cups)",
        first.lower()
    )

    if attached_unit_match:
        quantity = float(attached_unit_match.group(1))
        raw_unit = attached_unit_match.group(2)

        unit = UNIT_MAP.get(raw_unit, raw_unit)

        return quantity, None, None, 1, unit

    # Mixed whole number + Unicode fraction
    # e.g. 1½
    mixed_unicode_match = re.fullmatch(
        r"(\d+)([½⅓⅔¼¾⅛⅜⅝⅞])",
        first
    )

    if mixed_unicode_match:
        whole = float(mixed_unicode_match.group(1))
        fraction = unicode_fractions[
            mixed_unicode_match.group(2)
        ]

        return whole + fraction, None, None, 1, None

    # Unicode fraction
    # e.g. ½
    if first in unicode_fractions:
        return unicode_fractions[first], None, None, 1, None

    # Mixed whole number + separate Unicode fraction, e.g. 1 ½
    # (The existing attached form, 1½, is handled above.)
    if len(parts) > 1 and parts[1] in unicode_fractions:
        try:
            whole = float(first)
            return whole + unicode_fractions[parts[1]], None, None, 2, None
        except ValueError:
            pass

    # Mixed number
    # e.g. 1 1/2
    if len(parts) > 1 and "/" in parts[1]:
        try:
            whole = float(first)
            fraction = float(Fraction(parts[1]))

            return whole + fraction, None, None, 2, None

        except (ValueError, ZeroDivisionError):
            pass

    # Fraction
    # e.g. 1/2
    try:
        if "/" in first:
            return float(Fraction(first)), None, None, 1, None

    except (ValueError, ZeroDivisionError):
        pass

    # Normal integer / decimal
    try:
        return float(first), None, None, 1, None

    except ValueError:
        return None, None, None, 0, None


# ---------------------------------------------------------
# SINGLE LINE PARSING
# ---------------------------------------------------------

def parse_recipe_line(line):
    line = clean_recipe_line(line)

    if not line:
        return None

    parts = line.split()

    # Header
    if is_recipe_header(line):
        return {
            "quantity": None,
            "quantity_min": None,
            "quantity_max": None,
            "unit": None,
            "ingredient": None,
            "note": None,
            "type": "header",
            "original_text": line
        }

    (
        quantity,
        quantity_min,
        quantity_max,
        quantity_parts,
        attached_unit
    ) = parse_quantity(parts)

    # -----------------------------------------------------
    # QUANTITY RANGE
    # -----------------------------------------------------

    if quantity_min is not None and quantity_max is not None:

        # e.g. 80-120g breadcrumbs
        if attached_unit is not None:
            ingredient_parts = parts[quantity_parts:]
            ingredient_parts = remove_leading_of(
                ingredient_parts
            )

            ingredient = " ".join(
                ingredient_parts
            )

            ingredient, note = split_ingredient_and_note(
                ingredient
            )

            return {
                "quantity": None,
                "quantity_min": quantity_min,
                "quantity_max": quantity_max,
                "unit": attached_unit,
                "ingredient": ingredient,
                "note": note,
                "type": "measurable_range",
                "original_text": line
            }

        # e.g. 1-2 tbsp milk
        if (
            len(parts) > quantity_parts
            and parts[quantity_parts].lower()
            in KNOWN_UNITS
        ):
            unit = UNIT_MAP[
                parts[quantity_parts].lower()
            ]

            ingredient_parts = (
                parts[quantity_parts + 1:]
            )

            ingredient_parts = remove_leading_of(
                ingredient_parts
            )

            ingredient = " ".join(
                ingredient_parts
            )

            ingredient, note = split_ingredient_and_note(
                ingredient
            )

            return {
                "quantity": None,
                "quantity_min": quantity_min,
                "quantity_max": quantity_max,
                "unit": unit,
                "ingredient": ingredient,
                "note": note,
                "type": "measurable_range",
                "original_text": line
            }

    # -----------------------------------------------------
    # NO QUANTITY
    # -----------------------------------------------------

    if quantity is None:
        return {
            "quantity": None,
            "quantity_min": None,
            "quantity_max": None,
            "unit": None,
            "ingredient": line,
            "note": None,
            "type": "text",
            "original_text": line
        }

    # -----------------------------------------------------
    # ATTACHED UNIT
    # e.g. 150g flour
    # -----------------------------------------------------

    if attached_unit is not None:
        ingredient_parts = parts[quantity_parts:]
        ingredient_parts = remove_leading_of(
            ingredient_parts
        )

        ingredient = " ".join(
            ingredient_parts
        )

        ingredient, note = split_ingredient_and_note(
            ingredient
        )

        return {
            "quantity": quantity,
            "quantity_min": None,
            "quantity_max": None,
            "unit": attached_unit,
            "ingredient": ingredient,
            "note": note,
            "type": "measurable",
            "original_text": line
        }

    # -----------------------------------------------------
    # SEPARATE UNIT
    # e.g. 2 cups flour / 2 cups of flour
    # -----------------------------------------------------

    if (
        len(parts) > quantity_parts
        and parts[quantity_parts].lower()
        in KNOWN_UNITS
    ):
        unit = UNIT_MAP[
            parts[quantity_parts].lower()
        ]

        ingredient_parts = (
            parts[quantity_parts + 1:]
        )

        ingredient_parts = remove_leading_of(
            ingredient_parts
        )

        ingredient = " ".join(
            ingredient_parts
        )

        ingredient, note = split_ingredient_and_note(
            ingredient
        )

        return {
            "quantity": quantity,
            "quantity_min": None,
            "quantity_max": None,
            "unit": unit,
            "ingredient": ingredient,
            "note": note,
            "type": "measurable",
            "original_text": line
        }

    # -----------------------------------------------------
    # COUNT
    # e.g. 2 eggs / 1 onion
    # -----------------------------------------------------

    ingredient_parts = parts[quantity_parts:]

    ingredient = " ".join(
        ingredient_parts
    )

    ingredient, note = split_ingredient_and_note(
        ingredient
    )

    return {
        "quantity": quantity,
        "quantity_min": None,
        "quantity_max": None,
        "unit": None,
        "ingredient": ingredient,
        "note": note,
        "type": "count",
        "original_text": line
    }


# ---------------------------------------------------------
# FULL RECIPE PARSING
# ---------------------------------------------------------

def parse_recipe_text(recipe_text):
    rows = []

    for line in recipe_text.splitlines():
        parsed = parse_recipe_line(line)

        if parsed is not None:
            rows.append(parsed)

    return pd.DataFrame(rows)