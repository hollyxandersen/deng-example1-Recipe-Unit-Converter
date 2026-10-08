import pandas as pd
from fractions import Fraction
import re

KNOWN_UNITS = {
    "g", "gram", "grams",
    "ml", "mls","millilitre", "millilitres",
    "cup", "cups",
    "tbsp","tbsps", "tablespoon", "tablespoons",
    "tsp","tsps", "teaspoon", "teaspoons",
    "l", "litre", "litres",
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
    "teaspoons": "tsp",

    "l": "l",
    "litre": "l",
    "litres": "l",
}



def clean_recipe_line(line):
    line = line.strip()

    # Remove leading symbols/bullets/checkboxes until the first
    # letter, digit, or common fraction character
    line = re.sub(
        r"^[^A-Za-z0-9½⅓⅔¼¾⅛⅜⅝⅞]+",
        "",
        line
    )

    return line.strip()

def is_recipe_header(line):
    line_clean = line.strip().lower()

    return (
        line_clean.startswith("for the ")
        or line_clean.startswith("for ")
    )



def parse_recipe_line(line):
    line = clean_recipe_line(line)

    if not line:
        return None

    parts = line.split()

    if is_recipe_header(line):
        return {
            "quantity": None,
            "quantity_min": None,
            "quantity_max": None,
            "unit": None,
            "ingredient": None,
            "type": "header",
            "original_text": line
        }

    quantity, quantity_min, quantity_max, quantity_parts, attached_unit = parse_quantity(parts)

    

        # Quantity range e.g. 1-2 tbsp or 80-120g
    if quantity_min is not None and quantity_max is not None:

        # Unit attached directly to range e.g. 80-120g
        if attached_unit is not None:
            ingredient = " ".join(parts[quantity_parts:])

            return {
                "quantity": None,
                "quantity_min": quantity_min,
                "quantity_max": quantity_max,
                "unit": attached_unit,
                "ingredient": ingredient,
                "type": "measurable_range",
                "original_text": line
            }

        # Unit appears as next token e.g. 1-2 tbsp
        if (
            len(parts) > quantity_parts
            and parts[quantity_parts].lower() in KNOWN_UNITS
        ):
            unit = UNIT_MAP[parts[quantity_parts].lower()]
            ingredient = " ".join(parts[quantity_parts + 1:])

            return {
                "quantity": None,
                "quantity_min": quantity_min,
                "quantity_max": quantity_max,
                "unit": unit,
                "ingredient": ingredient,
                "type": "measurable_range",
                "original_text": line
        }

    # No numeric quantity at the start
        if quantity is None:
            return {
                "quantity": None,
                "quantity_min": None,
                "quantity_max": None,   
                "unit": None,
                "ingredient": line,
                "type": "text",
                "original_text": line
            }
        
    # Quantity and unit were stuck together e.g. 150g, 250ml
    if attached_unit is not None:
        ingredient = " ".join(parts[quantity_parts:])

        return {
            "quantity": quantity,
            "quantity_min": None,
            "quantity_max": None,
            "unit": attached_unit,
            "ingredient": ingredient,
            "type": "measurable",
            "original_text": line
        }


    # Numeric quantity followed by a recognised measurement unit
    if (
        len(parts) > quantity_parts
        and parts[quantity_parts].lower() in KNOWN_UNITS
    ):
        unit = UNIT_MAP[parts[quantity_parts].lower()]

        ingredient = " ".join(
            parts[quantity_parts + 1:]
        )

        return {
            "quantity": quantity,
            "quantity_min": None,
            "quantity_max": None,
            "unit": unit,
            "ingredient": ingredient,
            "type": "measurable",
            "original_text": line
        }

    # Numeric quantity, but no recognised measurement unit
    ingredient = " ".join(parts[quantity_parts:])

    return {
        "quantity": quantity,
        "quantity_min": None,
        "quantity_max": None,
        "unit": None,
        "ingredient": ingredient,
        "type": "count",
        "original_text": line
    }


def parse_quantity(parts):
    """
    Parse a quantity from the beginning of a split recipe line.

    Returns:
        quantity: float or None
        quantity_min: float or None
        quantity_max: float or None
        consumed_parts: number of text parts used for the quantity
        attached_unit: unit found in the same token as the quantity, or None
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

    # Range with attached unit e.g. 80-120g
    range_attached_match = re.fullmatch(
        r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)(g|kg|ml|l|tsp|tbsp|cup|cups)",
        first.lower()
    )

    if range_attached_match:
        quantity_min = float(range_attached_match.group(1))
        quantity_max = float(range_attached_match.group(2))
        raw_unit = range_attached_match.group(3)

        unit = UNIT_MAP.get(raw_unit, raw_unit)

        return None, quantity_min, quantity_max, 1, unit

    # Range with separate unit e.g. 1-2 tbsp
    range_match = re.fullmatch(
        r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)",
        first
    )

    if range_match:
        quantity_min = float(range_match.group(1))
        quantity_max = float(range_match.group(2))

        return None, quantity_min, quantity_max, 1, None

    # Quantity with attached unit e.g. 150g, 250ml
    attached_unit_match = re.fullmatch(
        r"(\d+(?:\.\d+)?)(g|kg|ml|l|tsp|tbsp|cup|cups)",
        first.lower()
    )

    if attached_unit_match:
        quantity = float(attached_unit_match.group(1))
        raw_unit = attached_unit_match.group(2)

        unit = UNIT_MAP.get(raw_unit, raw_unit)

        return quantity, None, None, 1, unit

    # Mixed whole number + Unicode fraction e.g. 1½
    mixed_unicode_match = re.fullmatch(
        r"(\d+)([½⅓⅔¼¾⅛⅜⅝⅞])",
        first
    )

    if mixed_unicode_match:
        whole = float(mixed_unicode_match.group(1))
        fraction = unicode_fractions[mixed_unicode_match.group(2)]

        return whole + fraction, None, None, 1, None

    # Unicode fraction e.g. ½
    if first in unicode_fractions:
        return unicode_fractions[first], None, None, 1, None

    # Mixed number e.g. 1 1/2
    if len(parts) > 1 and "/" in parts[1]:
        try:
            whole = float(first)
            fraction = float(Fraction(parts[1]))

            return whole + fraction, None, None, 2, None

        except (ValueError, ZeroDivisionError):
            pass

    # Fraction e.g. 1/2
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



def parse_recipe_text(recipe_text):
    rows = []

    for line in recipe_text.splitlines():
        parsed = parse_recipe_line(line)

        if parsed is not None:
            rows.append(parsed)

    return pd.DataFrame(rows)
