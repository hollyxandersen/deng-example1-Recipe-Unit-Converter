"""Matching and arithmetic using small, invented reference data.

The numbers are chosen to make expected answers easy to calculate.
They are not a copy of the live ExactCup dataset.
"""

import pandas as pd
import pytest

from transform import (
    make_ingredient_dataframe,
    make_alias_dataframe,
    match_recipe_ingredients,
    find_ingredient_candidates,
    convert_to_grams,
    convert_to_per_portion,
    convert_from_grams,
)


@pytest.fixture
def ingredients():
    """Pytest supplies a fresh reference table to each test that requests it."""
    return make_ingredient_dataframe({"ingredients": [
        {
            "slug": "flour",
            "name": "Plain Flour",
            "aliases": ["flour", "plain flour", "flour"],
            "grams_per_us_cup": 120,
            "grams_per_us_tablespoon": 7.5,
            "grams_per_us_teaspoon": 2.5,
            "grams_per_ml": 0.5,
        },
        {
            "slug": "brown-sugar",
            "name": "Brown Sugar (Packed)",
            "aliases": [],
            "grams_per_us_cup": 200,
            "grams_per_us_tablespoon": 12.5,
            "grams_per_us_teaspoon": 200 / 48,
            "grams_per_ml": 0.8,
        },
    ]})


def test_alias_lookup_includes_names_and_removes_duplicates(ingredients):
    result = make_alias_dataframe(ingredients)
    assert set(result.itertuples(index=False, name=None)) == {
        ("flour", "flour"),
        ("flour", "plain flour"),
        ("brown-sugar", "brown sugar"),
    }
    assert len(result) == 3


def test_matching_normalises_names_and_keeps_unknown_rows(ingredients):
    recipe = pd.DataFrame({
        "row_id": [0, 1],
        "ingredient": ["  PLAIN-FLOUR  ", "moon dust"],
    })
    result = match_recipe_ingredients(
        recipe, make_alias_dataframe(ingredients), ingredients
    ).set_index("row_id")
    assert len(result) == 2
    assert result.loc[0, "slug"] == "flour"
    assert result.loc[0, "grams_per_us_cup"] == 120
    assert pd.isna(result.loc[1, "slug"])
    assert result.loc[1, "ingredient"] == "moon dust"


def test_candidate_search_finds_broader_ingredient_name(ingredients):
    result = find_ingredient_candidates(
        "sugar", make_alias_dataframe(ingredients), ingredients
    )
    assert result["slug"].tolist() == ["brown-sugar"]


@pytest.mark.parametrize("unit, quantity, expected_grams", [
    ("g", 100, 100),
    ("kg", 0.5, 500),
    ("cup", 2, 240),
    ("tbsp", 2, 15),
    ("tsp", 3, 7.5),
    ("ml", 100, 50),
    ("l", 0.5, 250),
])
def test_convert_to_grams(ingredients, unit, quantity, expected_grams):
    recipe = ingredients.iloc[[0]].copy()
    recipe["unit"] = unit
    recipe["quantity"] = quantity
    result = convert_to_grams(recipe)
    assert result.iloc[0]["grams"] == pytest.approx(expected_grams)


def test_normalise_to_one_portion():
    recipe = pd.DataFrame({"grams": [240.0]})
    result = convert_to_per_portion(recipe, original_portions=4)
    assert result.iloc[0]["grams_per_portion"] == 60


@pytest.mark.parametrize("output_unit, expected_quantity, display_unit", [
    ("g", 360, "g"),
    ("cup", 3, "cup"),
    ("original", 3, "cup"),
])
def test_output_conversion_and_portion_scaling(
    ingredients, output_unit, expected_quantity, display_unit
):
    # 60 g per portion, scaled to 6 portions = 360 g = 3 test cups.
    recipe = ingredients.iloc[[0]].copy()
    recipe["grams_per_portion"] = 60.0
    recipe["unit"] = "cup"
    recipe["output_unit"] = output_unit
    result = convert_from_grams(recipe, desired_portions=6)
    assert result.iloc[0]["converted_quantity"] == pytest.approx(expected_quantity)
    assert result.iloc[0]["display_unit"] == display_unit
