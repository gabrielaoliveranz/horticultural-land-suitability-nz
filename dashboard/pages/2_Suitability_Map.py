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

Level colours (colorblind-safe fix, replacing the original green/gold/
red scheme): an Impeccable accessibility audit ran an actual deuteranopia/
protanopia simulation (via the `colorspacious` library — a real
simulation, not eyeballed) on the original brand-palette fill colors and
found a genuine WCAG 1.4.1 failure: under protanopia, Excellent's green
and Marginal's red simulated to near-identical muddy olive tones (RGB
distance 31.5, down from 183.2 with normal vision — an 83% collapse).
That's a real problem specifically for this page, since the map's only
per-parcel signal is fill hue (the tooltip's text label is a fallback
that requires hovering each parcel individually, not a substitute for
at-a-glance scanning).

Replaced with a diverging blue -> amber -> deep-orange scheme (deep blue
best, deep orange worst — blue and orange sit on the S-cone axis, which
red-green CVD doesn't affect). Re-verified the same way, on the actual
alpha-blended-over-background colors (not just the raw fill RGB, since
that's what a viewer actually sees):

  deuteranomaly: Excellent-Good 217.8, Excellent-Marginal 156.8, Good-Marginal 110.1
  protanomaly:   Excellent-Good 188.7, Excellent-Marginal 133.7, Good-Marginal 120.6

Worst-case pair distance is now 110.1 vs. the original scheme's 31.5 — a
~3.5x improvement, and comfortably above the ~50-60 threshold where
ColorBrewer/Okabe-Ito-style palettes are generally considered reliably
distinguishable under CVD simulation.

One deliberate finding from verifying rather than assuming: an earlier
draft of this fix graduated fill *opacity* by level (more opaque for
better scores) as a second visual channel. Simulating that against this
page's light background showed it actively hurts discriminability —
lower opacity washes every color toward the same light grey background,
pulling Good and Marginal closer together, not further apart (Good-
Marginal distance dropped to ~63-68 with graduated opacity vs. ~110-120
with it removed). So opacity is uniform (200) across all three levels,
same as the original scheme, and the secondary non-color cue is border
line width instead (thin for Excellent, thicker for Marginal) — doesn't
touch hue/opacity at all, so it can't undermine the CVD fix, and gives
WCAG 1.4.1 a genuine second channel beyond color alone.

This is a deliberate, documented deviation from PRODUCT.md's brand
palette for this one map's data encoding — accessibility on the
flagship page's primary visual signal outweighs brand-palette
consistency here. The rest of the app still uses the confirmed brand
colors; this exception is scoped to LEVEL_COLORS only.

Regression note (caught and fixed before shipping this change): the
first version of the line-width secondary cue blanked both the map AND
its basemap entirely — not a color problem, a pydeck one. pydeck's
Layer class treats any plain string kwarg as a deck.gl JS expression
(prefixing it with "@@="), so `line_width_units="pixels"` silently
became the expression `pixels` (undefined), which threw during Deck
construction and crashed the whole render, not just that one line-width
prop — confirmed via `layer.to_json()` showing `"lineWidthUnits":
"@@=pixels"` before the fix. pydeck's own escape hatch for a literal
string value is wrapping it in quote characters (bindings/layer.py's
QUOTE_CHARS check), so it's passed as `line_width_units="'pixels'"`
here, not `"pixels"`.

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

Empty-state guard: this page had the same latent bug that crashed
Expansion Candidates ("Invalid LngLat object: (NaN, NaN)") — a subzone
filter yielding zero rows would send GeoDataFrame.total_bounds()'s
all-NaN result straight into pydeck.ViewState. Every named subzone
currently has scored parcels, so this was never triggered here, but
it's the identical code pattern, so it gets the identical fix: an
`if len(view) == 0` branch with st.info() instead of building the map.
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

# Colorblind-safe diverging blue -> orange scheme, replacing the
# original green/gold/red brand colors — see module docstring's "Level
# colours" note for the verified deuteranopia/protanopia numbers.
LEVEL_COLORS = {
    "Excellent": [0, 63, 145, 200],     # deep blue
    "Good": [255, 176, 46, 200],        # amber
    "Marginal": [196, 57, 0, 200],      # deep orange
}

# Secondary, non-color visual cue (WCAG 1.4.1: color must not be the
# only signal) — border width in pixels, thin to thick as suitability
# drops. Deliberately not opacity: graduated opacity was verified to
# hurt colorblind discriminability against this page's light background
# (see docstring), so it stays uniform and line width carries the
# second channel instead.
LEVEL_LINE_WIDTHS = {
    "Excellent": 0.5,
    "Good": 1.0,
    "Marginal": 2.0,
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
    merged["line_width"] = merged["suitability_level"].map(LEVEL_LINE_WIDTHS)
    return merged


def to_geojson(gdf):
    cols = [
        "parcel_id", "suitability_score", "subzone", "suitability_level",
        "fill_color", "line_width", "geometry",
    ]
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

    if len(view) == 0:
        # Same latent bug class as Expansion Candidates — see module
        # docstring's "Empty-state guard" note. Every named subzone
        # currently has scored parcels, so this isn't reachable today,
        # but it gets the same guard rather than relying on that.
        st.info(f"No scored parcels found for “{subzone}”.")
    else:
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
            get_line_width="properties.line_width",
            # pydeck's Layer treats any plain string kwarg as a deck.gl
            # JS expression (prefixing it with "@@="), which broke this:
            # "pixels" became the expression `pixels` (undefined),
            # throwing during Deck construction and blanking the whole
            # map, not just this one prop (confirmed via l.to_json() —
            # "lineWidthUnits": "@@=pixels" — before this fix). Wrapping
            # in explicit quote characters is pydeck's documented escape
            # hatch (bindings/layer.py's QUOTE_CHARS check) for a literal
            # string value instead of an expression.
            line_width_units="'pixels'",
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
# colour-key row underneath, built from the same LEVEL_COLORS /
# LEVEL_LINE_WIDTHS dicts the map itself uses (single source of truth,
# can't drift out of sync). Swatch border thickness mirrors each
# level's line_width, so the legend documents both visual channels
# (color and border), not just color.
legend_swatches = "".join(
    f'<span style="display:inline-flex; align-items:center; margin-right:1.5rem;">'
    f'<span style="display:inline-block; width:14px; height:14px; border-radius:3px; '
    f'background:rgb({r},{g},{b}); border:{LEVEL_LINE_WIDTHS[level] * 1.5}px solid rgba(0,0,0,0.45); '
    f'margin-right:0.4rem;"></span>{level}</span>'
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
