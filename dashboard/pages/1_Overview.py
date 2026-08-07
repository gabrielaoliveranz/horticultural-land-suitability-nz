# =============================================================================
# TERROIR — Overview page
# Script: pages/1_Overview.py
# Stage:  Dashboard (Fase 5)
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Region-wide summary: KPI row (parcels ingested, parcels scored, %
Excellent) plus a bar chart of the Excellent/Good/Marginal split, both
from `suitability_levels_summary` / `parcel_scores` / `parcel_attributes`
in terroir.db — see docs/methodology.md, "Regional summary and expansion
candidates (business questions 1 and 2)".

Summary numbers only, no map (that's 2_Suitability_Map.py) and no
5-named-subzone breakdown (that's a future addition — subzone_summary
covers it). Functional, minimal styling for now; full polish is a later
pass, same as 0_Intro.py's.

Robustness note: load_overview_data() reindexes onto LEVEL_ORDER instead
of using .loc[LEVEL_ORDER] directly. All 3 levels currently have
parcels, so this isn't reachable today, but suitability_levels_summary
is a GROUP BY — if any level ever had zero parcels, its row simply
wouldn't exist in the query result, and .loc[] on a missing index label
raises KeyError (an unguarded raw traceback, not a handled empty
state). reindex(..., fill_value=0) is the same-shaped fix as the
empty-state guards on the map pages: assume the data can legitimately
be missing a category, and degrade to a visible 0 rather than crash.

Design-system pass: shared accent_divider()/footer()/card_css() from
components.py, same as every other page now. The KPI row gets the card
treatment (subtle border/tint) via card_css("kpi-card") plus
style_metrics("kpi-card") for accent-coloured values and an uppercase
eyebrow label — see those functions' docstrings for why this addresses
the design audit's "flatness" finding.

Accessibility: Streamlit's bar chart (Vega-Lite under the hood) already
ships a baseline role="graphics-document" — checked via the rendered
DOM before assuming it needed fixing — but its aria-label defaults to
the generic "Vega visualization", which says nothing about what the
chart actually shows. set_aria_label() overrides it with the real
content description.

Second design-audit pass (interactivity): switched from st.bar_chart to
st.altair_chart for two things st.bar_chart's simple API can't do —
a hover state (each bar lightens to a computed 40%-white-blended shade
of its own colour, not a single flat hover colour) and humanised tooltip
labels (real column titles instead of the raw "suitability_level"/
"parcel_count" field names the default Vega tooltip showed — confirmed
via an actual hover test in the earlier audit, not assumed). Bars are
now coloured by LEVEL_PALETTE_HEX (components.py) — the same
colourblind-safe blue/amber/orange scheme as the Suitability Map, for
one consistent colour language across the app. This chart isn't the
colourblind-risk case the map was: each bar already has a text label on
the x-axis, so colour isn't the only signal here (WCAG 1.4.1 is already
satisfied independent of the palette choice) — reusing the map's
palette is about visual consistency, not an accessibility requirement
on this specific chart.

Copy pass (corpo tone): the caption named the actual 4 districts
instead of the internal-sounding "4 target territorial authorities" —
same fact, plainer business language.

Design-token pass: the KPI row now renders as 3 separate cards
(metric_row()) instead of one shared container — each number is
visually independent, not grouped into a single rectangle. The chart's
axis label colour was a real WCAG failure (Vega-Lite's default grey
measured 3.02:1 against the page background, confirmed via a
contrast audit, not assumed) — overridden to theme.CHART_AXIS_COLOR
(5.44:1, computed with margin, not picked freehand).
"""

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "dashboard"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))
import theme  # noqa: E402
from components import (  # noqa: E402
    LEVEL_PALETTE_HEX,
    LEVEL_PALETTE_HOVER_HEX,
    accent_divider,
    footer,
    metric_row,
    section_header,
    set_aria_label,
)
from config import DB_PATH, get_connection  # noqa: E402

LEVEL_ORDER = ["Excellent", "Good", "Marginal"]


@st.cache_data
def load_overview_data():
    with get_connection(DB_PATH) as conn:
        levels = pd.read_sql("SELECT * FROM suitability_levels_summary", conn)
        n_scored = pd.read_sql("SELECT COUNT(*) AS n FROM parcel_scores", conn).iloc[0, 0]
        n_ingested = pd.read_sql("SELECT COUNT(*) AS n FROM parcel_attributes", conn).iloc[0, 0]
    levels = levels.set_index("suitability_level").reindex(LEVEL_ORDER, fill_value=0).reset_index()
    return levels, int(n_scored), int(n_ingested)


levels, n_scored, n_ingested = load_overview_data()
excellent_pct = levels.loc[levels["suitability_level"] == "Excellent", "pct"].iloc[0]

st.title("Overview")
st.caption(
    "Region-wide suitability breakdown across Tauranga City, Western Bay "
    "of Plenty, Ōpōtiki, and Whakatāne districts."
)

metric_row([
    ("Parcels ingested", f"{n_ingested:,}"),
    ("Parcels scored", f"{n_scored:,}"),
    ("% Excellent", f"{excellent_pct:.1f}%"),
])

accent_divider()

section_header("Suitability levels, region-wide")

levels["color"] = levels["suitability_level"].map(LEVEL_PALETTE_HEX)
levels["hover_color"] = levels["suitability_level"].map(LEVEL_PALETTE_HOVER_HEX)

TOOLTIP = [
    alt.Tooltip("suitability_level:N", title="Suitability level"),
    alt.Tooltip("parcel_count:Q", title="Parcels", format=","),
]
hover = alt.selection_point(on="pointerover", fields=["suitability_level"], nearest=True, empty=False)

# Two layers, not a single conditional Color encoding: alt.condition()
# with a field-based Color on BOTH branches hits a real bug in this
# Altair version (6.2.2) — `Color has no parameter named 'empty'`/
# `'field'`, confirmed by isolating it in a standalone repro before
# assuming the fix was elsewhere. A field-condition against a plain
# alt.value() else-branch works fine, but that can't vary the *base*
# colour per category. The standard Vega-Lite workaround is what's used
# here: a base layer (always-visible, per-category colour) plus a
# highlight layer (the lighter hover colour, opacity-conditional on the
# same selection) stacked exactly on top — opacity conditions against a
# single value are unaffected by the bug above.
# Vega-Lite's default axis label/title grey failed contrast (see
# module docstring) — theme.CHART_AXIS_COLOR applies everywhere labels
# render, both axes, both layers (the highlight layer needs its own
# copy too since Vega-Lite axis config isn't shared across layers in a
# LayerChart).
AXIS = alt.Axis(labelAngle=0, labelColor=theme.CHART_AXIS_COLOR, titleColor=theme.CHART_AXIS_COLOR)
Y_AXIS = alt.Axis(labelColor=theme.CHART_AXIS_COLOR, titleColor=theme.CHART_AXIS_COLOR)

base = alt.Chart(levels).mark_bar().encode(
    x=alt.X("suitability_level:N", sort=LEVEL_ORDER, title=None, axis=AXIS),
    y=alt.Y("parcel_count:Q", title="Parcels", axis=Y_AXIS),
    color=alt.Color("color:N", scale=None, legend=None),
    tooltip=TOOLTIP,
)
highlight = alt.Chart(levels).mark_bar().encode(
    x=alt.X("suitability_level:N", sort=LEVEL_ORDER),
    y=alt.Y("parcel_count:Q"),
    color=alt.Color("hover_color:N", scale=None, legend=None),
    opacity=alt.condition(hover, alt.value(1), alt.value(0)),
    tooltip=TOOLTIP,
).add_params(hover)

chart = (base + highlight).properties(height=350)
st.altair_chart(chart, use_container_width=True)

excellent_n = levels.loc[levels["suitability_level"] == "Excellent", "parcel_count"].iloc[0]
good_n = levels.loc[levels["suitability_level"] == "Good", "parcel_count"].iloc[0]
marginal_n = levels.loc[levels["suitability_level"] == "Marginal", "parcel_count"].iloc[0]
set_aria_label(
    '[data-testid="stVegaLiteChart"]',
    f"Bar chart of parcel counts by suitability level: {excellent_n:,} Excellent, "
    f"{good_n:,} Good, {marginal_n:,} Marginal.",
)

footer()
