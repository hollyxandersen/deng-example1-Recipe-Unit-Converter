import streamlit as st
import pandas as pd

from api import load_ingredient_data, get_cache_status, CACHE_MAX_AGE_DAYS
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
    /* --- Warm recipe-card design, refined to match the original sketch --- */
    :root {
        --recipe-orange: #D95C20;
        --recipe-orange-deep: #C74F16;
        --recipe-orange-soft: #E8A06C;
        --recipe-peach: #F7D7AF;
        --recipe-cream: #FBF2E4;
        --recipe-cream-2: #FFF9F1;
        --recipe-ink: #2F2A26;
        --recipe-muted: #7C6F67;
        --recipe-border: #6B4B39;
    }

    .stApp {
        background: #FCF8F3;
    }

    .block-container {
        max-width: 1100px;
        padding-top: 1.15rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 { margin-top: 0; }

    h1 {
        color: var(--recipe-orange-deep) !important;
        font-size: clamp(2.55rem, 4vw, 3.35rem) !important;
        letter-spacing: -0.045em;
        line-height: 1.02;
        font-weight: 760 !important;
        margin-bottom: 0.8rem !important;
    }

    /* Overall joined shell */
    .st-key-app_shell {
        background: linear-gradient(to right, var(--recipe-peach) 0%, var(--recipe-peach) 43%, var(--recipe-cream) 43%, var(--recipe-cream) 100%);
        border: 2px solid var(--recipe-border);
        border-radius: 28px;
        padding: 0 !important;
        overflow: hidden;
        box-shadow: 0 10px 32px rgba(92, 57, 35, 0.07);
    }

    .st-key-app_shell > div {
        padding: 0 !important;
    }

    .st-key-app_shell [data-testid="stHorizontalBlock"] {
        gap: 0 !important;
        align-items: stretch;
    }

    /* Panels */
    .st-key-input_panel {
        background: var(--recipe-peach);
        padding: 1.7rem 1.35rem 1.4rem;
        min-height: 700px;
        border-right: 2px solid rgba(107, 75, 57, 0.45);
    }

    .st-key-output_panel {
        background: var(--recipe-cream);
        padding: 1.7rem 1.45rem 1.45rem;
        min-height: 700px;
    }

    .st-key-input_panel h3 {
        color: var(--recipe-orange-deep) !important;
        font-size: 1.55rem !important;
        font-weight: 760 !important;
        padding-bottom: 0.6rem;
        border-bottom: 2px solid rgba(217, 92, 32, 0.5);
        margin-bottom: 0.9rem !important;
    }

    .st-key-input_panel label,
    .st-key-output_panel label {
        color: var(--recipe-ink) !important;
        font-weight: 560;
    }

    /* Ingredient input and number fields */
    .st-key-input_panel textarea {
        background: var(--recipe-cream-2) !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        border-radius: 15px !important;
        color: var(--recipe-ink) !important;
        line-height: 1.65 !important;
    }

    .st-key-input_panel [data-testid="stNumberInput"] input,
    .st-key-input_panel [data-testid="stNumberInput"] button {
        background: var(--recipe-cream-2) !important;
    }

    .st-key-input_panel [data-testid="stNumberInput"] > div {
        border-radius: 12px;
    }

    .st-key-input_panel [data-testid="stNumberInput"] [data-testid="stWidgetLabel"] p {
        font-size: 0.83rem;
    }

    .st-key-input_panel [data-testid="stToggle"] p {
        font-size: 0.85rem;
    }

    .st-key-input_panel hr {
        border-color: rgba(217, 92, 32, 0.35) !important;
        margin-top: 2rem !important;
        margin-bottom: 1.8rem !important;
    }

    /* Right-hand global unit selector */
    .st-key-output_panel [data-testid="stRadio"] > label p {
        font-size: 0.8rem;
        font-weight: 700;
        color: var(--recipe-muted);
    }

    .st-key-output_panel [data-testid="stRadio"] [role="radiogroup"] {
        border: 1px solid #E6C2A3;
        border-radius: 13px;
        padding: 0.35rem 0.6rem;
        background: #FFF1DE;
        gap: 0.8rem;
        width: fit-content;
    }

    .st-key-output_panel [data-testid="stRadio"] [role="radiogroup"] label {
        font-size: 0.85rem;
    }

    /* Selectboxes: force warm cream instead of default grey */
    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"] > div > div,
    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"] * {
        background: #FFF8EF !important;
    }

    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        border: 1px solid #E7CCB5 !important;
        border-radius: 12px !important;
        color: var(--recipe-ink) !important;
        box-shadow: none !important;
    }

    .st-key-output_panel [data-testid="stSelectbox"] svg {
        fill: #7E6C61 !important;
    }

    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within {
        border-color: var(--recipe-orange) !important;
        box-shadow: 0 0 0 1px rgba(217, 92, 32, 0.22) !important;
    }

    .st-key-output_panel [data-testid="stCaptionContainer"] {
        color: var(--recipe-muted);
        margin-bottom: 1rem;
    }

    .recipe-line {
        padding: 0.52rem 0;
        font-size: 1.02rem;
        color: var(--recipe-ink);
        line-height: 1.55;
    }

    .recipe-note {
        color: var(--recipe-muted);
        font-style: italic;
        padding: 0.45rem 0.55rem;
        white-space: normal;
        overflow-wrap: anywhere;
        word-break: break-word;
        background: rgba(255, 224, 188, 0.24);
        border-radius: 8px;
    }

    .recipe-header {
        color: var(--recipe-orange-deep);
        font-weight: 760;
        margin-top: 1.6rem;
        margin-bottom: 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-size: 0.84rem;
    }

    .cache-note {
        font-size: 0.78rem;
        color: var(--recipe-muted);
        line-height: 1.5;
    }

    /* Disabled cache refresh remains visibly disabled */
    .st-key-input_panel button {
        border-radius: 10px !important;
    }

    .st-key-input_panel button:disabled {
        opacity: 0.62;
    }

    @media (max-width: 760px) {
        .block-container { padding: 1rem 0.75rem 2rem; }
        .st-key-app_shell {
            border-radius: 20px;
        }
        .st-key-app_shell [data-testid="stHorizontalBlock"] {
            gap: 0 !important;
        }
        .st-key-input_panel,
        .st-key-output_panel {
            min-height: 0;
            padding: 1.15rem 1rem;
        }
        .st-key-input_panel {
            border-right: 0;
            border-bottom: 2px solid rgba(107, 75, 57, 0.3);
        }
    }

    /* Streamlit's header can otherwise leave a bright strip above the page. */
    [data-testid="stHeader"],
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"] {
        background-color: #FCF8F3 !important;
    }
    [data-testid="stDecoration"] { display: none !important; }

    /* Stretch the two Streamlit columns to the same height. */
    .st-key-app_shell [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        display: flex;
        flex-direction: column;
        align-self: stretch;
    }
    .st-key-app_shell [data-testid="stHorizontalBlock"] > [data-testid="column"] > div,
    .st-key-app_shell [data-testid="stHorizontalBlock"] > [data-testid="column"] > div > div {
        flex-grow: 1;
    }
    .st-key-app_shell .st-key-input_panel,
    .st-key-app_shell .st-key-output_panel {
        flex: 1 1 auto;
    }

    /* The outer BaseWeb text-area wrapper is the only visible border. */
    .st-key-input_panel [data-testid="stTextArea"] [data-baseweb="textarea"] {
        background: #FFF9F1 !important;
        border: 1px solid #E6B58D !important;
        border-radius: 15px !important;
        overflow: hidden;
        box-shadow: none !important;
    }
    .st-key-input_panel [data-testid="stTextArea"] textarea:focus {
        box-shadow: none !important;
    }
    .st-key-input_panel [data-testid="stTextArea"] [data-baseweb="textarea"]:focus-within {
        border-color: var(--recipe-orange) !important;
    }

    /* Streamlit / BaseWeb selectboxes: override the combobox itself, not
       merely its outer wrapper (which leaves the familiar grey fill). */
    .st-key-app_shell [data-testid="stSelectbox"] [role="combobox"],
    .st-key-app_shell [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    .st-key-app_shell [data-testid="stSelectbox"] [data-baseweb="select"] > div > div {
        background-color: #FFF4E4 !important;
        background-image: none !important;
    }
    .st-key-app_shell [data-testid="stSelectbox"] [role="combobox"] {
        border: 1px solid #E7CCB5 !important;
        border-radius: 11px !important;
    }
    .st-key-app_shell [data-testid="stSelectbox"] [aria-disabled="true"] {
        opacity: .72;
    }
    @media (max-width: 760px) {
        .st-key-app_shell {
            background: var(--recipe-cream);
        }
        .st-key-app_shell [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            display: block;
        }
    }
    /* Final control polish: one crisp textarea border, no nested outlines. */
    .st-key-input_panel [data-testid="stTextArea"] [data-baseweb="textarea"] {
        border: 1.5px solid #D99C70 !important;
        border-radius: 13px !important;
        overflow: hidden !important;
        background: #FFF9F1 !important;
        box-shadow: none !important;
    }
    .st-key-input_panel [data-testid="stTextArea"] textarea {
        border: 0 !important;
        outline: 0 !important;
        box-shadow: none !important;
        border-radius: 0 !important;
        background: transparent !important;
    }
    .st-key-input_panel [data-testid="stTextArea"] [data-baseweb="textarea"]:focus-within {
        border-color: var(--recipe-orange) !important;
    }

    /* Match the right panel, including the arrow area of the closed dropdown. */
    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"],
    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"] > div > div,
    .st-key-output_panel [data-testid="stSelectbox"] [role="combobox"],
    .st-key-output_panel [data-testid="stSelectbox"] [role="combobox"] * {
        background-color: var(--recipe-cream) !important;
        background-image: none !important;
    }
    .st-key-output_panel [data-testid="stSelectbox"] [role="combobox"] {
        border: 1px solid #DCC8B3 !important;
        border-radius: 10px !important;
        box-shadow: none !important;
    }
    .st-key-output_panel [data-testid="stSelectbox"] [role="combobox"]:focus-within {
        border-color: var(--recipe-orange) !important;
    }

    /* Make the number field and the +/- buttons one seamless control. */
    .st-key-input_panel [data-testid="stNumberInput"] [data-baseweb="input"],
    .st-key-input_panel [data-testid="stNumberInput"] [data-baseweb="input"] > div,
    .st-key-input_panel [data-testid="stNumberInput"] input,
    .st-key-input_panel [data-testid="stNumberInput"] button,
    .st-key-input_panel [data-testid="stNumberInput"] button * {
        background-color: #FFF9F1 !important;
        background-image: none !important;
        box-shadow: none !important;
    }
    .st-key-input_panel [data-testid="stNumberInput"] [data-baseweb="input"] {
        border-radius: 10px !important;
        overflow: hidden !important;
    }
    .st-key-input_panel [data-testid="stNumberInput"] button {
        border-radius: 0 !important;
    }
    .st-key-input_panel [data-testid="stNumberInput"] button:hover {
        background-color: #F5E0CA !important;
    }

    /* V5 overrides: apply to the actual BaseWeb widget subtree, not only
       the text area inside it. The page background is #FCF8F3. */
    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"],
    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"] *:not(svg):not(path),
    .st-key-output_panel [data-testid="stSelectbox"] [role="combobox"],
    .st-key-output_panel [data-testid="stSelectbox"] [role="combobox"] *:not(svg):not(path) {
        background: #FCF8F3 !important;
        background-color: #FCF8F3 !important;
        background-image: none !important;
    }
    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        border: 1px solid #E2C6AD !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }
    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"] svg {
        background: transparent !important;
    }

    /* Streamlit renders stepper controls as their own buttons and wrappers;
       repaint these too, so there are no grey blocks around +/- . */
    .st-key-input_panel [data-testid="stNumberInput"] :is(
        [data-baseweb="input"],
        [data-baseweb="input"] *,
        [data-testid="stNumberInputStepDown"],
        [data-testid="stNumberInputStepUp"],
        [data-testid="stNumberInputStepDown"] *,
        [data-testid="stNumberInputStepUp"] *,
        button,
        button > div
    ):not(svg):not(path) {
        background: #FFF9F1 !important;
        background-color: #FFF9F1 !important;
        background-image: none !important;
    }
    .st-key-input_panel [data-testid="stNumberInput"] button {
        border: 0 !important;
        border-radius: 0 !important;
        box-shadow: none !important;
    }
    .st-key-input_panel [data-testid="stNumberInput"] button:hover,
    .st-key-input_panel [data-testid="stNumberInput"] button:hover > div {
        background: #F4DFC8 !important;
    }

    /* V6: the shell's zero-gap rule should not collapse nested portion columns. */
    .st-key-input_panel [data-testid="stHorizontalBlock"] {
        gap: 0.85rem !important;
    }

    /* One continuous select control, without a nested outlined textbox. */
    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background: #FCF8F3 !important;
        border: 1px solid #DEC4AD !important;
        border-radius: 10px !important;
        box-shadow: none !important;
        overflow: hidden !important;
    }
    .st-key-output_panel [data-testid="stSelectbox"] [role="combobox"],
    .st-key-output_panel [data-testid="stSelectbox"] [role="combobox"]:focus,
    .st-key-output_panel [data-testid="stSelectbox"] [role="combobox"]:focus-within,
    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"] > div > div {
        background: #FCF8F3 !important;
        border: 0 !important;
        outline: 0 !important;
        box-shadow: none !important;
        border-radius: 0 !important;
    }
    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within {
        border-color: #D95C20 !important;
        box-shadow: 0 0 0 1px rgba(217,92,32,0.18) !important;
    }
    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"] > div > div:last-child,
    .st-key-output_panel [data-testid="stSelectbox"] [data-baseweb="select"] svg {
        background: #FCF8F3 !important;
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

# Never automatically refresh an existing cache. A first-run download
# happens only when ingredients.json does not exist.
try:
    data = load_ingredient_data()
except (RuntimeError, ValueError, OSError) as exc:
    st.error(f"Ingredient reference data could not be loaded: {exc}")
    st.stop()

cache_status = get_cache_status()

ingredients_df = make_ingredient_dataframe(data)
alias_df = make_alias_dataframe(ingredients_df)


# ---------------------------------------------------------
# APP
# ---------------------------------------------------------

st.markdown("<h1>Recipe Unit Converter</h1>", unsafe_allow_html=True)

with st.container(key="app_shell", border=False):

    input_col, output_col = st.columns(
        [0.43, 0.57],
        gap="large"
    )

    # =====================================================
    # LEFT PANEL
    # =====================================================

    with input_col, st.container(key="input_panel"):

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

        portion_col1, portion_col2 = st.columns(2, gap="small")

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

        if cache_status["exists"]:
            cache_date = cache_status["cached_at"].strftime("%d %b %Y")
            st.markdown(
                f'<div class="cache-note">Local cache saved: {cache_date} '
                f'({cache_status["age_days"]} days ago)</div>',
                unsafe_allow_html=True
            )

        if cache_status["stale"]:
            st.caption(f"Local cache is at least {CACHE_MAX_AGE_DAYS} days old. "
                       "You can refresh it when ready.")

        if st.button(
            "Refresh cache",
            disabled=not cache_status["stale"],
            help=("Download updated reference data" if cache_status["stale"]
                  else f"Available when the cache is {CACHE_MAX_AGE_DAYS} days old"),
        ):
            try:
                load_ingredient_data(force_refresh=True)
            except (RuntimeError, ValueError, OSError) as exc:
                st.error(f"Refresh failed. Your existing cache was kept. Details: {exc}")
            else:
                st.session_state["cache_refresh_message"] = "Ingredient cache refreshed successfully."
                st.rerun()

        if st.session_state.pop("cache_refresh_message", None):
            st.success("Ingredient cache refreshed successfully.")

    # =====================================================
    # RIGHT PANEL
    # =====================================================

    with output_col, st.container(key="output_panel"):

        preference = st.radio(
            "Default units",
            ["Keep original", "Grams", "Cups"],
            horizontal=True
        )

        st.caption(
            "Can't convert an ingredient? Try simplifying or clarifying its name — "
            "for example, “unsalted butter” → “butter”. " \
            "If an ingredient has several possible matches, use the dropdown to select an option."
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

            # Ranges carry two quantities but still need ingredient matching.
            measurable_rows = parsed_recipe[
                parsed_recipe["type"].isin(["measurable", "measurable_range"])
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

                elif row_type in ("measurable", "measurable_range"):

                    matching_row = matched_recipe[
                        matched_recipe["row_id"] == parsed_row["row_id"]
                    ].copy()

                    if matching_row.empty:
                        continue

                    # Both endpoints of a range share one ingredient match.
                    is_range = row_type == "measurable_range"
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

                        if is_range:
                            scaled_min = parsed_row["quantity_min"] * scale_factor
                            scaled_max = parsed_row["quantity_max"] * scale_factor
                            quantity_text = (
                                f"{format_number(scaled_min)}–{format_number(scaled_max)}"
                            )
                        else:
                            quantity_text = format_number(
                                parsed_row["quantity"] * scale_factor
                            )

                        ingredient_col, unit_col = output_placeholder.columns(
                            [0.73, 0.27],
                            vertical_alignment="center"
                        )

                        with ingredient_col:
                            st.markdown(
                                f"""
                                <div class="recipe-line">
                                    {quantity_text}
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

                    # Convert after ingredient selection. For a range, send
                    # both endpoints through the same existing conversion pipeline.
                    if is_range:
                        endpoint_rows = pd.concat(
                            [matching_row.copy(), matching_row.copy()],
                            ignore_index=True
                        )
                        endpoint_rows["quantity"] = [
                            parsed_row["quantity_min"],
                            parsed_row["quantity_max"],
                        ]
                    else:
                        endpoint_rows = matching_row

                    grams_rows = convert_to_grams(endpoint_rows)
                    per_portion_rows = convert_to_per_portion(
                        grams_rows, original_portions
                    )
                    converted_rows = convert_from_grams(
                        per_portion_rows, desired_portions
                    )

                    if is_range:
                        quantities = converted_rows["converted_quantity"].tolist()
                        quantity_text = (
                            f"{format_number(quantities[0])}–"
                            f"{format_number(quantities[1])}"
                        )
                    else:
                        quantity_text = format_number(
                            converted_rows.iloc[0]["converted_quantity"]
                        )
                    display_unit = converted_rows.iloc[0]["display_unit"]

                    with ingredient_col:
                        st.markdown(
                            f"""
                            <div class="recipe-line">
                                {quantity_text}
                                {display_unit}
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

    #python -m streamlit run app.py