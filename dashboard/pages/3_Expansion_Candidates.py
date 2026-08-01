# =============================================================================
# TERROIR — Expansion Candidates page
# Script: pages/3_Expansion_Candidates.py
# Stage:  Dashboard (Fase 5)
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Parcel-level map of expansion_candidates (business question 2) — geometry
from parcels_linz.geojson joined on source_id, same load/simplify/render
pattern as 2_Suitability_Map.py. Colored and filterable by LCDB class
instead of suitability level, plus a subzone filter (5 named + "outside"
+ "All").

Urban exclusion (display-layer fix, not yet in the underlying data):
expansion_candidates as computed by 08_regional_summary_expansion.py
includes parcels classified as "Built-up Area (settlement)" and "Urban
Parkland/Open Space" — land that's already built on, not genuine
horticultural expansion land. This was flagged as a gap the first time
candidates were sampled for external verification (2 of that sample's
Katikati rows were exactly this). It was never fixed upstream, so this
page excludes those 2 classes itself: 1,658 of 13,041 candidates
(12.7%) are dropped, leaving 11,383 shown here. This is reasonable for
now but is a display-layer patch, not a real fix — logged in
docs/methodology.md as a refinement to push back into
08_regional_summary_expansion.py itself, so every consumer of
expansion_candidates gets the correct set, not just this page.

LCDB class colors are a functional placeholder: 22 distinct classes
remain after the urban exclusion, far more than the confirmed 5-colour
brand palette was ever meant to cover (that palette is for suitability
levels). Colors here are an evenly-spaced hue rotation, not a styled
brand palette — real categorical design is future work, same "minimal
styling for now" framing as every other page so far.

Geometry is simplified/rounded the same way and for the same reason as
2_Suitability_Map.py (full precision exceeds Streamlit's message size
limit for large views) — see that page's docstring for the numbers.

Empty-combination handling: subzone x LCDB class is filtered as one
combination, and most combinations are legitimately empty (69 of 132
possible pairs — smaller subzones like Opotiki only have 3 of the 22
classes present at all). An empty `view` previously crashed pydeck
("Invalid LngLat object: (NaN, NaN)") because
`GeoDataFrame.total_bounds()` on zero rows returns all-NaN, which flowed
straight into `pydeck.ViewState`. Confirmed this was not a join/filter
bug — the geometry merge and boolean-mask filtering both preserve row
counts and the geometry column exactly as expected; the missing piece
was simply no empty-state branch. Fixed by checking `len(view) == 0`
before touching pydeck at all and showing an st.info() message instead.
"""

import colorsys
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

# Display-layer fix — see module docstring's "Urban exclusion" note.
EXCLUDED_LCDB_CLASSES = {"Built-up Area (settlement)", "Urban Parkland/Open Space"}

# Confirmed live against expansion_candidates minus EXCLUDED_LCDB_CLASSES.
LCDB_CLASSES = [
    "Broadleaved Indigenous Hardwoods", "Deciduous Hardwoods", "Estuarine Open Water",
    "Exotic Forest", "Fernland", "Forest - Harvested", "Gorse and/or Broom",
    "Gravel and Rock", "Herbaceous Freshwater Vegetation", "Herbaceous Saline Vegetation",
    "High Producing Exotic Grassland", "Indigenous Forest", "Lake or Pond",
    "Low Producing Grassland", "Mangrove", "Manuka and/or Kanuka",
    "Mixed Exotic Shrubland", "River", "Sand and Gravel", "Short-rotation Cropland",
    "Surface Mine or Dump", "Transport Infrastructure",
]
LCDB_CLASS_OPTIONS = ["All"] + LCDB_CLASSES

NAMED_SUBZONES = ["Tauranga", "Te Puke", "Pongakawa", "Katikati", "Opotiki"]
OUTSIDE_SUBZONES_LABEL = "Outside the 5 named subzones"
SUBZONE_OPTIONS = ["All", *NAMED_SUBZONES, OUTSIDE_SUBZONES_LABEL]

# Same tolerance/precision and same reason as 2_Suitability_Map.py.
SIMPLIFY_TOLERANCE_DEG = 0.00001   # ~1m at this latitude
PRECISION_GRID_DEG = 1e-6          # 6 decimal places, ~11cm


def build_lcdb_color_palette(classes):
    n = len(classes)
    colors = {}
    for i, cls in enumerate(classes):
        hue = i / n
        r, g, b = colorsys.hls_to_rgb(hue, 0.45, 0.55)
        colors[cls] = [int(r * 255), int(g * 255), int(b * 255), 200]
    return colors


LCDB_COLORS = build_lcdb_color_palette(LCDB_CLASSES)


@st.cache_data
def load_candidate_data():
    with sqlite3.connect(DB_PATH) as conn:
        candidates = pd.read_sql("SELECT * FROM expansion_candidates", conn)
    candidates = candidates[~candidates["lcdb_class_2023"].isin(EXCLUDED_LCDB_CLASSES)]

    parcels = geopandas.read_file(PARCELS_PATH, columns=["source_id", "parcel_id", "geometry"])
    parcels["geometry"] = parcels.geometry.simplify(SIMPLIFY_TOLERANCE_DEG, preserve_topology=True)
    parcels["geometry"] = parcels.geometry.apply(
        lambda g: shapely.set_precision(g, grid_size=PRECISION_GRID_DEG)
    )

    merged = parcels.merge(candidates, on="source_id", how="inner")
    merged["fill_color"] = merged["lcdb_class_2023"].map(LCDB_COLORS)
    return merged


def to_geojson(gdf):
    cols = ["parcel_id", "suitability_score", "lcdb_class_2023", "subzone", "fill_color", "geometry"]
    return gdf[cols].__geo_interface__


st.title("Expansion Candidates")
st.caption(
    "Parcels with excellent-to-good soil suitability that aren't already under "
    "orchard/vineyard/perennial-crop use — see docs/methodology.md, \"Regional "
    "summary and expansion candidates (business questions 1 and 2)\"."
)
st.caption(
    "Urban/settlement land cover (\"Built-up Area (settlement)\", \"Urban "
    "Parkland/Open Space\") is excluded on this page — a display-layer fix, "
    "logged in docs/methodology.md as a refinement still to be pushed back "
    "into 08_regional_summary_expansion.py itself."
)

subzone = st.selectbox("Subzone", SUBZONE_OPTIONS)
lcdb_class = st.selectbox("LCDB class", LCDB_CLASS_OPTIONS)

with st.spinner("Loading candidates..."):
    all_candidates = load_candidate_data()

    st.metric("Candidates (urban/settlement excluded)", f"{len(all_candidates):,}")

    if subzone == "All":
        view = all_candidates
    elif subzone == OUTSIDE_SUBZONES_LABEL:
        view = all_candidates[all_candidates["subzone"].isna()]
    else:
        view = all_candidates[all_candidates["subzone"] == subzone]

    if lcdb_class != "All":
        view = view[view["lcdb_class_2023"] == lcdb_class]

    st.caption(f"Showing {len(view):,} of {len(all_candidates):,} candidates.")

    if len(view) == 0:
        # Real, common UI state, not an edge case: most subzones only
        # have a handful of the 22 LCDB classes actually present (e.g.
        # Opotiki has just 3), so 69 of the 132 possible subzone x class
        # combinations are legitimately empty — confirmed against the
        # data, not a join/filter bug (GeoDataFrame.total_bounds() on an
        # empty frame returns [nan, nan, nan, nan], which previously
        # crashed pydeck with "Invalid LngLat object: (NaN, NaN)").
        # Skip building a view/layer/deck entirely rather than feeding
        # pydeck NaN coordinates.
        st.info(
            f"No candidates match “{subzone}” + “{lcdb_class}”. "
            "Try a different combination — most subzones only have a handful "
            "of the 22 LCDB classes present at all."
        )
    else:
        bounds = view.total_bounds  # minx, miny, maxx, maxy
        view_state = pydeck.ViewState(
            longitude=(bounds[0] + bounds[2]) / 2,
            latitude=(bounds[1] + bounds[3]) / 2,
            zoom=12 if subzone not in ("All", OUTSIDE_SUBZONES_LABEL) else 9,
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
                "html": "<b>Parcel:</b> {parcel_id}<br/>"
                        "<b>Score:</b> {suitability_score}<br/>"
                        "<b>LCDB class:</b> {lcdb_class_2023}<br/>"
                        "<b>Subzone:</b> {subzone}",
                "style": {"backgroundColor": "#0B4F3D", "color": "white"},
            },
        )

        st.pydeck_chart(deck, height=600)
