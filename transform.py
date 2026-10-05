import pandas as pd

def make_ingredient_dataframe(data):
    # Convert the ingredients list from the JSON response into a DataFrame
    ingredients_df = pd.DataFrame(data["ingredients"])
    return ingredients_df

def make_alias_dataframe(ingredients_df):
    alias_df = ingredients_df[["slug", "name", "aliases"]].explode("aliases") #Split aliases to rows

    # Create a second lookup table containing each canonical ingredient name.
    # Rename the lookup column to match_name so it can be stacked with the aliases.

    alias_df = alias_df.rename(columns={"aliases": "match_name"})

    canonical_names = ingredients_df[["slug", "name"]].copy()
    canonical_names = canonical_names.rename(columns={"name": "match_name"})

    #Remove notes from match name in parentheses eg brown sugar (packed)
    canonical_names["match_name"] = (
    canonical_names["match_name"]
    .str.replace(r"\s*\([^)]*\)", "", regex=True)
    .str.lower()
    .str.strip()
)

    #Union the two tables (slug and match_name columns only)
    alias_df = pd.concat(
        [
            alias_df[["slug", "match_name"]],
            canonical_names
        ],
        ignore_index=True
    )

    #Remove nulls from match_name and clean the data so it is consistently lowercase with no leading/trailing spaces
    alias_df = alias_df.dropna(subset=["match_name"])
    alias_df["match_name"] = alias_df["match_name"].str.lower().str.strip()

    return alias_df


def match_recipe_ingredients(recipe_df, alias_df, ingredients_df):
    # Create a cleaned ingredient name for matching
    recipe_df = recipe_df.copy()

    recipe_df["match_name"] = (
        recipe_df["ingredient"]
        .str.lower()
        .str.strip()
    )

    # Match recipe ingredient names to canonical ingredient slugs
    recipe_matched = recipe_df.merge(
        alias_df,
        on="match_name",
        how="left"
    )

    # Add the full ExactCup ingredient data
    recipe_enriched = recipe_matched.merge(
        ingredients_df,
        on="slug",
        how="left",
        suffixes=("", "_reference")
    )

    return recipe_enriched


def convert_to_grams(recipe_df):
    recipe_df = recipe_df.copy()

    def calculate_grams(row):
        unit = row["unit"]
        quantity = row["quantity"]

        if unit == "g":
            return quantity

        elif unit == "cup":
            return quantity * row["grams_per_us_cup"]

        elif unit == "tbsp":
            return quantity * row["grams_per_us_tablespoon"]

        elif unit == "tsp":
            return quantity * row["grams_per_us_teaspoon"]

        elif unit == "ml":
            return quantity * row["grams_per_ml"]

        else:
            return None

    recipe_df["grams"] = recipe_df.apply(calculate_grams, axis=1)

    return recipe_df