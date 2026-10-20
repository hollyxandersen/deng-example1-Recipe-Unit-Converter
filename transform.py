import pandas as pd
import re


# ---------------------------------------------------------
# MATCHING HELPERS
# ---------------------------------------------------------

def normalise_match_name(value):
    """
    Standardise ingredient names before matching.

    Example:
        self-raising flour
        self raising flour

    both become:
        self raising flour
    """

    return (
        value
        .str.lower()
        .str.replace("-", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


# ---------------------------------------------------------
# REFERENCE TABLES
# ---------------------------------------------------------

def make_ingredient_dataframe(data):
    """
    Convert the ingredient portion of the API response
    into a DataFrame.
    """

    ingredients_df = pd.DataFrame(
        data["ingredients"]
    )

    return ingredients_df


def make_alias_dataframe(ingredients_df):
    """
    Create a lookup table containing one possible
    ingredient name per row and its canonical slug.
    """

    # Split API alias lists into separate rows
    alias_df = ingredients_df[
        ["slug", "name", "aliases"]
    ].explode("aliases")

    alias_df = alias_df.rename(
        columns={"aliases": "match_name"}
    )

    # Add canonical ingredient names as valid match values
    canonical_names = ingredients_df[
        ["slug", "name"]
    ].copy()

    canonical_names = canonical_names.rename(
        columns={"name": "match_name"}
    )

    # Remove parenthetical source notes
    # e.g. Brown Sugar (Packed) -> Brown Sugar
    canonical_names["match_name"] = (
        canonical_names["match_name"]
        .str.replace(
            r"\s*\([^)]*\)",
            "",
            regex=True
        )
    )

    # Stack aliases and canonical names
    alias_df = pd.concat(
        [
            alias_df[
                ["slug", "match_name"]
            ],
            canonical_names
        ],
        ignore_index=True
    )

    # Remove empty aliases
    alias_df = alias_df.dropna(
        subset=["match_name"]
    )

    # Normalise all matching values
    alias_df["match_name"] = normalise_match_name(
        alias_df["match_name"]
    )

    # Remove duplicate lookup rows
    alias_df = alias_df.drop_duplicates(
        subset=["slug", "match_name"]
    )

    return alias_df

def find_ingredient_candidates(
    ingredient_name,
    alias_df,
    ingredients_df
):
    """
    Find possible API ingredients for a recipe ingredient.

    First searches for exact aliases.
    If none exist, searches for ingredient names
    containing the recipe ingredient as a whole word.
    """

    search_name = normalise_match_name(
        pd.Series([ingredient_name])
    ).iloc[0]

    # Look for exact matching aliases
    exact_matches = alias_df[
        alias_df["match_name"] == search_name
    ]

    if not exact_matches.empty:
        candidate_slugs = exact_matches["slug"].unique()

    else:
        # Find broader matches, e.g.
        # sugar -> caster sugar, brown sugar, etc.
        pattern = rf"\b{re.escape(search_name)}\b"

        broader_matches = alias_df[
            alias_df["match_name"].str.contains(
                pattern,
                regex=True,
                na=False
            )
        ]

        candidate_slugs = broader_matches["slug"].unique()

    # Get human-readable names for the dropdown
    candidates = ingredients_df[
        ingredients_df["slug"].isin(candidate_slugs)
    ][["slug", "name"]].drop_duplicates()

    return candidates.sort_values("name")


# ---------------------------------------------------------
# INGREDIENT MATCHING
# ---------------------------------------------------------

def match_recipe_ingredients(
    recipe_df,
    alias_df,
    ingredients_df
):

    recipe_df = recipe_df.copy()

    # First attempt:
    # match the complete parsed ingredient name
    recipe_df["match_name"] = normalise_match_name(
        recipe_df["ingredient"]
    )

    recipe_matched = recipe_df.merge(
        alias_df,
        on="match_name",
        how="left"
    )

    # -----------------------------------------------------
    # FALLBACK FOR "OR"
    #
    # Example:
    # sunflower or peanut oil
    #
    # First try whole phrase.
    # If that fails, try:
    #   sunflower
    # then:
    #   peanut oil
    # -----------------------------------------------------

    unmatched_mask = recipe_matched[
        "slug"
    ].isna()

    unmatched_indices = recipe_matched[
        unmatched_mask
    ].index

    for index in unmatched_indices:

        ingredient = recipe_matched.loc[
            index,
            "ingredient"
        ]

        if not isinstance(ingredient, str):
            continue

        if " or " not in ingredient.lower():
            continue

        alternatives = re.split(
            r"\s+or\s+",
            ingredient,
            maxsplit=1,
            flags=re.IGNORECASE
        )

        for alternative in alternatives:

            candidate = alternative.strip()

            candidate_match = normalise_match_name(
                pd.Series([candidate])
            ).iloc[0]

            result = alias_df[
                alias_df["match_name"]
                == candidate_match
            ]

            if not result.empty:

                recipe_matched.loc[
                    index,
                    "slug"
                ] = result.iloc[0]["slug"]

                recipe_matched.loc[
                    index,
                    "match_name"
                ] = candidate_match

                break

    # Attach full ExactCup conversion data
    recipe_enriched = recipe_matched.merge(
        ingredients_df,
        on="slug",
        how="left",
        suffixes=("", "_reference")
    )

    return recipe_enriched


# ---------------------------------------------------------
# CONVERT INPUT TO GRAMS
# ---------------------------------------------------------

def convert_to_grams(recipe_df):

    recipe_df = recipe_df.copy()

    def calculate_grams(row):

        unit = row["unit"]
        quantity = row["quantity"]

        if unit == "g":
            return quantity

        elif unit == "kg":
            return quantity * 1000

        elif unit == "cup":
            return (
                quantity
                * row["grams_per_us_cup"]
            )

        elif unit == "tbsp":
            return (
                quantity
                * row["grams_per_us_tablespoon"]
            )

        elif unit == "tsp":
            return (
                quantity
                * row["grams_per_us_teaspoon"]
            )

        elif unit == "ml":
            return (
                quantity
                * row["grams_per_ml"]
            )

        elif unit == "l":
            return (
                quantity
                * 1000
                * row["grams_per_ml"]
            )

        else:
            return None

    recipe_df["grams"] = recipe_df.apply(
        calculate_grams,
        axis=1
    )

    return recipe_df


# ---------------------------------------------------------
# NORMALISE TO ONE PORTION
# ---------------------------------------------------------

def convert_to_per_portion(
    recipe_df,
    original_portions
):

    recipe_df = recipe_df.copy()

    recipe_df["grams_per_portion"] = (
        recipe_df["grams"]
        / original_portions
    )

    return recipe_df


# ---------------------------------------------------------
# CONVERT GRAMS TO OUTPUT UNIT
# ---------------------------------------------------------

def convert_from_grams(
    recipe_df,
    desired_portions
):

    recipe_df = recipe_df.copy()

    recipe_df["scaled_grams"] = (
        recipe_df["grams_per_portion"]
        * desired_portions
    )

    def calculate_output(row):

        output_unit = row[
            "output_unit"
        ]

        if output_unit == "original":
            output_unit = row["unit"]

        grams = row["scaled_grams"]

        if output_unit == "g":
            return grams

        elif output_unit == "kg":
            return grams / 1000

        elif output_unit == "cup":
            return (
                grams
                / row["grams_per_us_cup"]
            )

        elif output_unit == "tbsp":
            return (
                grams
                / row["grams_per_us_tablespoon"]
            )

        elif output_unit == "tsp":
            return (
                grams
                / row["grams_per_us_teaspoon"]
            )

        elif output_unit == "ml":
            return (
                grams
                / row["grams_per_ml"]
            )

        elif output_unit == "l":
            return (
                grams
                / row["grams_per_ml"]
                / 1000
            )

        else:
            return None

    recipe_df["converted_quantity"] = (
        recipe_df.apply(
            calculate_output,
            axis=1
        )
    )

    recipe_df["display_unit"] = (
        recipe_df.apply(
            lambda row: (
                row["unit"]
                if row["output_unit"]
                == "original"
                else row["output_unit"]
            ),
            axis=1
        )
    )

    return recipe_df