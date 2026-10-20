import streamlit as st
import pandas as pd

from api import load_ingredient_data
from parser import parse_recipe_text
from transform import (
    make_ingredient_dataframe,
    make_alias_dataframe,
    match_recipe_ingredients,
    convert_to_grams,
    convert_to_per_portion,
    convert_from_grams,
    find_ingredient_candidates
)


# ---------------------------------------------------------
# PAGE SETUP
# ---------------------------------------------------------

st.set_page_config(
    page_title="Recipe Unit Converter",
    page_icon="🥄",
    layout="centered"
)

st.markdown(
    """
    <style>
        .block-container {
            max-width: 950px;
            padding-top: 3rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3 {
            margin-top: 0;
        }

        .recipe-line {
            padding: 0.3rem 0;
            font-size: 1.05rem;
        }

        .recipe-note {
            color: #777;
            font-style: italic;
            padding: 0.5rem 0.7rem;

            white-space: normal;
            overflow-wrap: anywhere;
            word-break: break-word;
        }

        .recipe-header {
            font-weight: 700;
            margin-top: 1.4rem;
            margin-bottom: 0.4rem;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }

        .cache-note {
            font-size: 0.8rem;
            color: #777;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def format_number(value):
    """Display recipe quantities without unnecessary decimals."""

    if value is None or pd.isna(value):
        return ""

    if float(value).is_integer():
        return str(int(value))

    return f"{value:.2f}".rstrip("0").rstrip(".")


def default_unit(original_unit, preference):
    """Choose the initial row-level unit from the global preference."""

    if preference == "Keep original":
        return "original"

    if preference == "Grams":
        return "g"

    if preference == "Cups":
        return "cup"

    return "original"


# ---------------------------------------------------------
# REFERENCE DATA
# ---------------------------------------------------------

data = load_ingredient_data()

ingredients_df = make_ingredient_dataframe(data)
alias_df = make_alias_dataframe(ingredients_df)


# ---------------------------------------------------------
# APP
# ---------------------------------------------------------

st.title("Recipe Unit Converter")

with st.container(border=True):

    input_col, output_col = st.columns(
        [0.43, 0.57],
        gap="large"
    )

    # =====================================================
    # LEFT PANEL
    # =====================================================

    with input_col:

        st.markdown("### Paste your ingredients")

        recipe_text = st.text_area(
            "Recipe ingredients",
            value="""2 cups plain flour
1 tbsp brown sugar
250 ml milk
1 onion
salt to taste""",
            height=260,
            label_visibility="collapsed"
        )

        portion_col1, portion_col2 = st.columns(2)

        with portion_col1:
            original_portions = st.number_input(
                "Original portions",
                min_value=1,
                value=4,
                step=1
            )

        with portion_col2:
            desired_portions = st.number_input(
                "Desired portions",
                min_value=1,
                value=4,
                step=1
            )

        show_text_rows = st.toggle(
            "Show notes and unscaled lines",
            value=True
        )

        st.divider()

        if "updated" in data:
            st.markdown(
                f"""
                <div class="cache-note">
                    Ingredient reference data updated: {data["updated"]}
                </div>
                """,
                unsafe_allow_html=True
            )

        st.button(
            "Refresh cache",
            disabled=True,
            help="Automatic cache refresh controls will be added later."
        )

    # =====================================================
    # RIGHT PANEL
    # =====================================================

    with output_col:

        preference = st.radio(
            "Default units",
            ["Keep original", "Grams", "Cups"],
            horizontal=True
        )

        st.caption(
            "Can't convert an ingredient? Try simplifying or clarifying its name — "
            "for example, “unsalted butter” → “butter”, or “sugar” → “caster sugar”."
        )

        if not recipe_text.strip():

            st.info("Paste a recipe to get started.")

        else:

            # -------------------------------------------------
            # PARSE RECIPE
            # -------------------------------------------------

            parsed_recipe = (
                parse_recipe_text(recipe_text)
                .reset_index(names="row_id")
            )

            # -------------------------------------------------
            # PREPARE MEASURABLE ROWS
            # -------------------------------------------------

            measurable_rows = parsed_recipe[
                parsed_recipe["type"] == "measurable"
            ].copy()

            if not measurable_rows.empty:

                matched_recipe = match_recipe_ingredients(
                    measurable_rows,
                    alias_df,
                    ingredients_df
                )

            else:
                matched_recipe = measurable_rows

            scale_factor = desired_portions / original_portions

            # -------------------------------------------------
            # RENDER RECIPE IN ORIGINAL ORDER
            # -------------------------------------------------

            for _, parsed_row in parsed_recipe.iterrows():

                row_type = parsed_row["type"]

                # =============================================
                # TEXT / UNPARSED LINES
                # =============================================

                if row_type == "text":

                    if show_text_rows:
                        st.markdown(
                            f"""
                            <div class="recipe-note">
                                {parsed_row["original_text"]}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    continue

                # =============================================
                # HEADERS
                # =============================================

                if row_type == "header":

                    st.markdown(
                        f"""
                        <div class="recipe-header">
                            {parsed_row["original_text"]}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                # =============================================
                # MEASURABLE INGREDIENTS
                # =============================================

                elif row_type == "measurable":

                    matching_row = matched_recipe[
                        matched_recipe["row_id"] == parsed_row["row_id"]
                    ].copy()

                    if matching_row.empty:
                        continue

                    # Reserve the output row above the ingredient-match selector.
                    output_placeholder = st.empty()

                    # Keep the ingredient's match dropdown beside its recipe row.
                    if matching_row["slug"].isna().iloc[0]:
                        candidates = find_ingredient_candidates(
                            parsed_row["ingredient"], alias_df, ingredients_df
                        )

                        if not candidates.empty:
                            options = {
                                candidate["name"]: candidate["slug"]
                                for _, candidate in candidates.iterrows()
                            }
                            selected_name = st.selectbox(
                                f"Match for {parsed_row['ingredient']}",
                                ["No match"] + list(options),
                                key=f"ingredient_match_{parsed_row['row_id']}",
                            )

                            if selected_name != "No match":
                                selected_slug = options[selected_name]
                                reference_row = ingredients_df[
                                    ingredients_df["slug"] == selected_slug
                                ].iloc[0]
                                matching_row["slug"] = selected_slug
                                for col in ingredients_df.columns:
                                    if col in ("slug", "aliases"):
                                        continue
                                    target_col = (
                                        f"{col}_reference"
                                        if f"{col}_reference" in matching_row.columns
                                        else col
                                    )
                                    matching_row[target_col] = reference_row[col]

                    can_convert = matching_row["slug"].notna().iloc[0]

                    # Ingredient parsed correctly,
                    # but ExactCup has no conversion data
                    if not can_convert:

                        scaled_quantity = (
                            parsed_row["quantity"]
                            * scale_factor
                        )

                        ingredient_col, unit_col = output_placeholder.columns(
                            [0.73, 0.27],
                            vertical_alignment="center"
                        )

                        with ingredient_col:
                            st.markdown(
                                f"""
                                <div class="recipe-line">
                                    {format_number(scaled_quantity)}
                                    {parsed_row["unit"]}
                                    {parsed_row["ingredient"]}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                        with unit_col:
                            st.selectbox(
                                "Unit",
                                ["original"],
                                key=f"unit_{parsed_row['row_id']}_unmatched",
                                disabled=True,
                                help="No conversion data is available for this ingredient.",
                                label_visibility="collapsed"
                            )

                        continue

                    # Ingredient has conversion data
                    original_unit = parsed_row["unit"]

                    unit_options = [
                        "original",
                        "g",
                        "ml",
                        "cup",
                        "tbsp",
                        "tsp"
                    ]

                    default = default_unit(
                        original_unit,
                        preference
                    )

                    default_index = unit_options.index(default)

                    ingredient_col, unit_col = output_placeholder.columns(
                        [0.73, 0.27],
                        vertical_alignment="center"
                    )

                    with unit_col:

                        chosen_unit = st.selectbox(
                            "Unit",
                            unit_options,
                            index=default_index,
                            key=f"unit_{parsed_row['row_id']}_{preference}",
                            label_visibility="collapsed"
                        )

                    matching_row["output_unit"] = chosen_unit

                    # Convert only after the user's ingredient choice is applied.
                    grams_row = convert_to_grams(matching_row)
                    per_portion_row = convert_to_per_portion(
                        grams_row, original_portions
                    )
                    converted_row = convert_from_grams(
                        per_portion_row, desired_portions
                    ).iloc[0]

                    with ingredient_col:

                        st.markdown(
                            f"""
                            <div class="recipe-line">
                                {format_number(converted_row["converted_quantity"])}
                                {converted_row["display_unit"]}
                                {parsed_row["ingredient"]}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                # =============================================
                # COUNT INGREDIENTS
                # e.g. 2 eggs, 1 onion
                # =============================================

                elif row_type == "count":

                    scaled_quantity = (
                        parsed_row["quantity"]
                        * scale_factor
                    )

                    st.markdown(
                        f"""
                        <div class="recipe-line">
                            {format_number(scaled_quantity)}
                            {parsed_row["ingredient"]}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                # =============================================
                # MEASURABLE RANGES
                # V1: scale range but retain original unit
                # =============================================

                elif row_type == "measurable_range":

                    scaled_min = (
                        parsed_row["quantity_min"]
                        * scale_factor
                    )

                    scaled_max = (
                        parsed_row["quantity_max"]
                        * scale_factor
                    )

                    st.markdown(
                        f"""
                        <div class="recipe-line">
                            {format_number(scaled_min)}–{format_number(scaled_max)}
                            {parsed_row["unit"]}
                            {parsed_row["ingredient"]}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                

    #python -m streamlit run app.py