import streamlit as st
import pandas as pd

from api import load_ingredient_data
from transform import (
    make_ingredient_dataframe,
    make_alias_dataframe,
    match_recipe_ingredients,
    convert_to_grams,
    convert_to_per_portion,
    convert_from_grams,
)

st.title("Recipe Converter")

# Reference data
data = load_ingredient_data()
ingredients_df = make_ingredient_dataframe(data)
alias_df = make_alias_dataframe(ingredients_df)

# Known-valid MVP recipe
recipe_data = [
    {"quantity": 2, "unit": "cup", "ingredient": "plain flour"},
    {"quantity": 1, "unit": "tbsp", "ingredient": "brown sugar"},
    {"quantity": 250, "unit": "ml", "ingredient": "milk"},
]

original_portions = 4

recipe_df = pd.DataFrame(recipe_data)

matched_recipe = match_recipe_ingredients(
    recipe_df,
    alias_df,
    ingredients_df
)

recipe_in_grams = convert_to_grams(matched_recipe)

recipe_per_portion = convert_to_per_portion(
    recipe_in_grams,
    original_portions
)

desired_portions = st.number_input(
    "Number of portions",
    min_value=1,
    value=4,
    step=1
)

st.subheader("Choose output units")

output_units = []

for index, row in recipe_per_portion.iterrows():
    output_unit = st.selectbox(
        row["ingredient"],
        ["original", "g", "ml", "cup", "tbsp", "tsp"],
        key=f"unit_{index}"
    )
    output_units.append(output_unit)

recipe_per_portion["output_unit"] = output_units

converted_recipe = convert_from_grams(
    recipe_per_portion,
    desired_portions
)

st.subheader("Converted recipe")

for _, row in converted_recipe.iterrows():
    st.write(
        f'{row["converted_quantity"]:.2f} '
        f'{row["display_unit"]} '
        f'{row["ingredient"]}'
    )