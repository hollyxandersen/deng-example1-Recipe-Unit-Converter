from parser import parse_recipe_line, parse_recipe_text
import pytest

def test_parse_fraction():
    """Check that a fractional quantity is parsed correctly."""

    result = parse_recipe_line("1/2 cup flour")

    assert result["quantity"] == 0.5
    assert result["unit"] == "cup"
    assert result["ingredient"] == "flour"
    assert result["type"] == "measurable"


@pytest.mark.parametrize("quantity_text", ["1 1/2", "1½", "1 ½"])
def test_parse_mixed_number(quantity_text):
    """A whole number and fraction should become one quantity."""
    result = parse_recipe_line(f"{quantity_text} cups flour")
    assert result["quantity"] == 1.5
    assert result["unit"] == "cup"
    assert result["ingredient"] == "flour"



def test_parse_attached_unit():
    """A measurement should work without a space before the unit."""
    result = parse_recipe_line("250ml milk")

    assert result["quantity"] == 250
    assert result["unit"] == "ml"
    assert result["ingredient"] == "milk"


def test_parse_quantity_range():
    """Both ends of a measurement range should be preserved."""
    result = parse_recipe_line("80-120g sugar")

    assert result["quantity_min"] == 80
    assert result["quantity_max"] == 120
    assert result["unit"] == "g"
    assert result["ingredient"] == "sugar"
    assert result["type"] == "measurable_range"


def test_parse_countable_ingredient():
    """An ingredient with a count but no unit should be classified."""
    result = parse_recipe_line("2 onions")

    assert result["quantity"] == 2
    assert result["unit"] is None
    assert result["ingredient"] == "onions"
    assert result["type"] == "count"


def test_preserve_unmeasured_text():
    """An unmeasured ingredient should remain available as text."""
    result = parse_recipe_line("salt to taste")

    assert result["quantity"] is None
    assert result["type"] == "text"
    assert result["original_text"] == "salt to taste"



@pytest.mark.parametrize("prefix", ["• ", "- ", "* "])
def test_leading_bullets_do_not_change_ingredient(prefix):
    """Leading bullet characters should be ignored."""
    result = parse_recipe_line(f"{prefix}2 cups flour")

    assert result["quantity"] == 2
    assert result["unit"] == "cup"
    assert result["ingredient"] == "flour"
    assert result["type"] == "measurable"


@pytest.mark.parametrize("line", ["2-3 onions", "2–3 onions"])
def test_unitless_range_is_preserved_as_text(line):
    # Current limitation: count ranges are retained, but not scaled.
    """Unitless ranges should be preserved as text."""

    result = parse_recipe_line(line)
    assert result["type"] == "text"
    assert result["quantity"] is None
    assert result["original_text"] == line


def test_optional_of_and_comma_note():
    """The word 'of' and a trailing note after a comma should be ignored."""
    result = parse_recipe_line("2 cups of flour, sifted")

    assert result["quantity"] == 2
    assert result["unit"] == "cup"
    assert result["ingredient"] == "flour"
    assert result["note"] == "sifted"


def test_recipe_preserves_order_and_skips_blank_lines():
    """A recipe should preserve the order of ingredients and skip blank lines."""
    result = parse_recipe_text("For the sauce:\n\n2 cups milk\nsalt to taste")

    assert result["type"].tolist() == ["header", "measurable", "text"]
    assert result["original_text"].tolist() == [
        "For the sauce:", "2 cups milk", "salt to taste"
    ]


def test_blank_line_is_ignored():
    assert parse_recipe_line("   ") is None
