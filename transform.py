import pandas as pd

def make_ingredient_dataframe(data):
    ingredients_df = pd.DataFrame(data["ingredients"])
    return ingredients_df

def make_alias_dataframe(ingredients_df):
    alias_df = ingredients_df[["slug", "name", "aliases"]].explode("aliases")

    alias_df = alias_df.rename(columns={"aliases": "match_name"})

    canonical_names = ingredients_df[["slug", "name"]].copy()
    canonical_names = canonical_names.rename(columns={"name": "match_name"})

    alias_df = pd.concat(
        [
            alias_df[["slug", "match_name"]],
            canonical_names
        ],
        ignore_index=True
    )

    alias_df = alias_df.dropna(subset=["match_name"])
    alias_df["match_name"] = alias_df["match_name"].str.lower().str.strip()

    return alias_df

   