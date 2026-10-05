import pandas as pd

original_portions = 4

#Fetch data from API or cache

from api import load_ingredient_data
data = load_ingredient_data()

from transform import (
    make_ingredient_dataframe,
    make_alias_dataframe,
    match_recipe_ingredients,
    convert_to_grams,
    convert_to_per_portion
)
ingredients_df = make_ingredient_dataframe(data)
alias_df = make_alias_dataframe(ingredients_df)


recipe_data = [
    {"quantity": 2, "unit": "cup", "ingredient": "plain flour"},
    {"quantity": 1, "unit": "tbsp", "ingredient": "brown sugar"},
    {"quantity": 250, "unit": "ml", "ingredient": "milk"},
]

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

print(
    recipe_per_portion[
        [
            "ingredient",
            "quantity",
            "unit",
            "grams",
            "grams_per_portion"
        ]
    ]
)