# =============================================================================
# TERROIR — Suitability Map page
# Script: pages/2_Suitability_Map.py
# Stage:  Dashboard (Fase 5)
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Parcel-level map: geometry from data/processed/parcels_linz.geojson,
joined on source_id with suitability_score and subzone from terroir.db.
Colored by suitability level (Excellent/Good/Marginal) via a pydeck
GeoJsonLayer, with a subzone filter (5 named Apophenia subzones + "All")
to narrow the view and keep rendering fast.

Only scored parcels are shown (inner join with parcel_scores) — the
1,343 parcels with no S-map match have no suitability_score to color by,
consistent with every other scoring page. Functional, minimal styling
for now, same as 0_Intro.py / 1_Overview.py.

Level colours are fill colours on a map, not text — per Impeccable's
contrast findings during 0_Intro.py's polish pass, lima green and
SunGold gold fail WCAG as *text* on the confirmed background (1.5-1.6:1)
but that constraint doesn't apply to map fills. Excellent/Good/Marginal
use primary green / SunGold gold / alert red — a green-gold-red gradient
reads faster on a map than two greens would (Good uses gold rather than
lima green for exactly this reason: clearer at-a-glance separation from
Excellent's green at small parcel sizes).

Geometry note: the "All" view (21,491 parcels) genuinely failed to
render at full precision — Streamlit's MessageSizeError, "Data of size
229.0 MB exceeds the message size limit of 200.0 MB" (confirmed live,
not just slow). Full-precision parcel boundaries carry far more
coordinate precision than a web map needs at any zoom this page uses, so
geometry is lightly simplified (~1m tolerance, topology-preserving) and
coordinates rounded to 6 decimal places (~11cm) before every render —
this cuts the raw GeoJSON size from 62.7MB to 23.8MB with no visible
shape loss, comfortably under the message limit. Applied once inside the
cached loader, not per filter change.

Below the map: a colour-key legend (Excellent/Good/Marginal, same
LEVEL_COLORS the map itself uses) and a short "How is this score
calculated?" expander summarising the weighting — a pointer to
docs/methodology.md's full reasoning, not a copy of it.

A spinner ("Loading map...") wraps only the data load + pydeck render —
the title, caption, and subzone selectbox above it stay instant/
interactive regardless of load time.
"""

import sqlite3
from pathlib import Path

import geopandas
import pandas as pd
import pydeck
import shapely
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PARCELS_PATH = PROJECT_ROOT / "data" / "processed" / "parcels_linz.geojson"
DB_PATH = PROJECT_ROOT / "data" / "processed" / "terroir.db"

# Same bins/right=False as 05_subzone_summary.py and
# 08_regional_summary_expansion.py — see docs/methodology.md, "Score
# distribution and suitability levels" (the boundary-bug fix).
LEVEL_BINS = [-float("inf"), 5.0, 8.0, float("inf")]
LEVEL_LABELS = ["Marginal", "Good", "Excellent"]

LEVEL_COLORS = {
    "Excellent": [11, 79, 61, 200],    # primary green
    "Good": [242, 169, 0, 200],        # SunGold gold
    "Marginal": [192, 57, 43, 200],    # alert red
}

SUBZONE_OPTIONS = ["All", "Tauranga", "Te Puke", "Pongakawa", "Katikati", "Opotiki"]

# See module docstring's "Geometry note" — full precision genuinely
# exceeds Streamlit's message size limit for the "All" view.
SIMPLIFY_TOLERANCE_DEG = 0.00001   # ~1m at this latitude
PRECISION_GRID_DEG = 1e-6          # 6 decimal places, ~11cm


@st.cache_data
def load_map_data():
    # Heaviest part of this page (a ~110MB file) — cached so it only
    # loads once per session, not on every filter change.
    parcels = geopandas.read_file(PARCELS_PATH, columns=["source_id", "parcel_id", "geometry"])
    parcels["geometry"] = parcels.geometry.simplify(SIMPLIFY_TOLERANCE_DEG, preserve_topology=True)
    parcels["geometry"] = parcels.geometry.apply(
        lambda g: shapely.set_precision(g, grid_size=PRECISION_GRID_DEG)
    )

    with sqlite3.connect(DB_PATH) as conn:
        # parcel_scores already carries subzone (copied at scoring time
        # in 04_calculate_score.py) — no join needed.
        scores = pd.read_sql("SELECT source_id, suitability_score, subzone FROM parcel_scores", conn)

    merged = parcels.merge(scores, on="source_id", how="inner")
    merged["suitability_level"] = pd.cut(
        merged["suitability_score"], bins=LEVEL_BINS, labels=LEVEL_LABELS, right=False,
    ).astype(str)
    merged["fill_color"] = merged["suitability_level"].map(LEVEL_COLORS)
    return merged


def to_geojson(gdf):
    cols = ["parcel_id", "suitability_score", "subzone", "suitability_level", "fill_color", "geometry"]
    return gdf[cols].__geo_interface__


st.title("Suitability Map")
st.caption(
    "Parcel-level suitability, colored by level. Only scored parcels are shown "
    "(1,343 parcels with no S-map match are excluded, same as elsewhere)."
)

subzone = st.selectbox("Subzone", SUBZONE_OPTIONS)

# Spinner wraps only the heavy part — data load + the pydeck render — not
# the title/caption/selectbox above (instant, always interactive) or the
# legend/expander below (static, no data dependency).
with st.spinner("Loading map..."):
    all_parcels = load_map_data()
    view = all_parcels if subzone == "All" else all_parcels[all_parcels["subzone"] == subzone]

    st.caption(f"Showing {len(view):,} of {len(all_parcels):,} scored parcels.")

    bounds = view.total_bounds  # minx, miny, maxx, maxy
    view_state = pydeck.ViewState(
        longitude=(bounds[0] + bounds[2]) / 2,
        latitude=(bounds[1] + bounds[3]) / 2,
        zoom=12 if subzone != "All" else 9,
    )

    layer = pydeck.Layer(
        "GeoJsonLayer",
        data=to_geojson(view),
        get_fill_color="properties.fill_color",
        get_line_color=[255, 255, 255, 60],
        line_width_min_pixels=0.5,
        stroked=True,
        filled=True,
        pickable=True,
        auto_highlight=True,
    )

    deck = pydeck.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={
            # Two independent {field} placeholders in one line — deck.gl
            # substitutes each property separately, no precomputed "display"
            # column needed to get "6.0 (Good)".
            "html": "<b>Parcel:</b> {parcel_id}<br/>"
                    "<b>Score:</b> {suitability_score} ({suitability_level})<br/>"
                    "<b>Subzone:</b> {subzone}",
            "style": {"backgroundColor": "#0B4F3D", "color": "white"},
        },
    )

    st.pydeck_chart(deck, height=600)

# Legend — pydeck has no native in-map legend, so this is a plain
# colour-key row underneath, built from the same LEVEL_COLORS dict the
# map itself uses (single source of truth, can't drift out of sync).
legend_swatches = "".join(
    f'<span style="display:inline-flex; align-items:center; margin-right:1.5rem;">'
    f'<span style="display:inline-block; width:14px; height:14px; border-radius:3px; '
    f'background:rgb({r},{g},{b}); margin-right:0.4rem;"></span>{level}</span>'
    for level, (r, g, b, _a) in LEVEL_COLORS.items()
)
st.html(f'<div style="display:flex; align-items:center; margin-top:0.5rem;">{legend_swatches}</div>')

with st.expander("How is this score calculated?"):
    st.markdown(
        "Each parcel's score (0-10) combines 4 S-map soil factors, each "
        "scored 0-10 and weighted:\n\n"
        "- **Soil order** — 40%\n"
        "- **Soil texture** — 40%\n"
        "- **Soil drainage** — 10%\n"
        "- **Soil depth** — 10%\n\n"
        "Soil order and texture vary a lot from parcel to parcel, so they "
        "carry most of the weight. Drainage and depth are heavily skewed "
        "toward one value region-wide (most parcels are \"Well drained\" "
        "and \"Deep\"), so they carry less.\n\n"
        "**Levels:** Excellent 8.0–10.0 · Good 5.0–7.9 · Marginal below 5.0."
    )
