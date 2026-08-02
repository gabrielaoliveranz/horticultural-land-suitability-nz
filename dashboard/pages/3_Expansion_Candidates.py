# =============================================================================
# TERROIR — Expansion Candidates page
# Script: pages/3_Expansion_Candidates.py
# Stage:  Dashboard (Fase 5)
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Parcel-level map of expansion_candidates (business question 2) — geometry
from parcels_linz.geojson joined on source_id, same load/simplify/render
pattern as 2_Suitability_Map.py. Coloured and filterable by LCDB class
instead of suitability level, plus a subzone filter (5 named + "outside"
+ "All").

Urban exclusion (display-layer fix, not yet in the underlying data):
expansion_candidates as computed by 08_regional_summary_expansion.py
includes parcels classified as "Built-up Area (settlement)" and "Urban
Parkland/Open Space" — land that's already built on, not genuine
horticultural expansion land. This was flagged as a gap the first time
candidates were sampled for external verification (2 of that sample's
Katikati rows were exactly this). It was never fixed upstream, so this
page excludes those 2 classes itself: 1,662 of 13,040 candidates
(12.7%) are dropped, leaving 11,378 shown here. This is reasonable for
now but is a display-layer patch, not a real fix — logged in
docs/methodology.md as a refinement to push back into
08_regional_summary_expansion.py itself, so every consumer of
expansion_candidates gets the correct set, not just this page.

LCDB class colours are a functional placeholder: 22 distinct classes
remain after the urban exclusion, far more than the confirmed 5-colour
brand palette was ever meant to cover (that palette is for suitability
levels). Colours here are an evenly-spaced hue rotation, not a styled
brand palette — real categorical design is future work, same "minimal
styling for now" framing as every other page so far.

Geometry arrives pre-simplified/rounded from src/01_ingest_linz.py (moved
there from this page's own runtime load — see that script's docstring
for why and 2_Suitability_Map.py's docstring for the fuller derivation,
not repeated here since it's no longer this page's own cost to justify).

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

Design-system + accessibility pass: shared accent_divider()/footer()/
card_css() from components.py, same as every other page. The KPI metric
gets the same card treatment as Overview's KPI row. The map gets a
hidden screen-reader description (sr_only) plus a role="img"/aria-label
set directly on the chart's DOM element (label_chart) — see
components.py's docstrings for why both exist rather than just one.

Copy pass (corpo tone): both intro captions referenced internal
implementation detail visitors don't need — a doc file path, "business
questions 1 and 2", "display-layer fix", and the upstream script
filename (08_regional_summary_expansion.py). All of that stays in this
docstring (where it belongs, for future maintainers) and was removed
from the visitor-facing captions, which now just state what's shown and
what's excluded, in plain terms.

Design-token pass: the KPI metric now renders via metric_row() (a
single-item card, same token as Overview's multi-metric row, for
consistency) instead of a manually key'd container. The urban-exclusion
note moved from a plain caption into a callout("info", ...) — genuinely
useful context worth a bit of visual weight, using the same token every
other callout on the app uses rather than a new one-off element (this
page was flagged as visually flat in the last review). The empty-state
message uses callout("info", ...) instead of st.info() for the same
reason as 2_Suitability_Map.py.

Performance pass (same technique as 2_Suitability_Map.py's, re-derived
against this page's own data rather than copied — the two pages' per-
subzone candidate counts turned out to look nothing alike, see below):

1. Default subzone changed from "All" to Pongakawa. This page's own
   distribution is lopsided in a way Suitability Map's isn't: Opotiki
   (36) and Katikati (39) — Suitability Map's own default — are both
   under 40 candidates here, too sparse to read as a real preview of
   an 11,378-candidate dataset. Tauranga (1,052) is the biggest named
   subzone; most candidates (9,654 of 11,378, ~85%) fall outside the 5
   named subzones entirely. Pongakawa (250) is the smallest subzone
   that still looks like a genuine dataset rather than a handful of
   dots — "small without being trivially empty," the same standard
   Suitability Map's own pick was reasoned against, just landing on a
   different subzone once actually checked against this page's counts.
2. Simplification tolerance loosened from ~1m to ~5m max deviation —
   same SIMPLIFY_TOLERANCE_DEG value as 2_Suitability_Map.py, and the
   same Douglas-Peucker guarantee / pixel-resolution math applies
   directly: identical source geometry, identical latitude, and this
   page uses the same zoom levels (12 for a named subzone, 9 for
   All/outside) — see that page's own docstring for the full
   derivation rather than repeating it here. Since moved upstream into
   src/01_ingest_linz.py — this page no longer pays the simplify cost
   at runtime, it just reads the already-~5m-tolerance file.
3. Audited to_geojson()'s column list against what the layer/tooltip
   actually reference: parcel_id, suitability_score, lcdb_class_2023,
   subzone, and fill_color are each read by either the tooltip HTML or
   the get_fill_color accessor — nothing unused was found to drop.

Measured payload sizes (compact JSON, same column set, actual
to_geojson() output — not estimated): "All" 15.14MB at the original
~1m tolerance -> 11.05MB at ~5m (-27%, matching Suitability Map's -26%
almost exactly — same geometry, same math, as expected). The new
Pongakawa default is 355.1KB at ~5m tolerance (vs. 546.6KB at ~1m) — a
visitor loading this page now downloads ~0.35MB instead of ~15MB by
default. For reference, every named subzone at ~5m: Tauranga 842.3KB,
Te Puke 475.8KB, Pongakawa 355.1KB, Katikati 28.6KB, Opotiki 22.7KB;
"outside the 5 named subzones" is 9.33MB, the one filter option still
heavier than "All" was pre-tolerance-fix, unavoidable given it's ~85%
of all candidates — one click away, not the default.

Simplification moved upstream (after the above payload numbers were
measured): this page's own load_candidate_data() used to call
shapely.simplify()/set_precision() on every cold cache miss, same as
2_Suitability_Map.py's load_map_data() — see src/01_ingest_linz.py's
docstring for why that got moved into ingestion instead. Payload sizes
above are unchanged (same tolerance, same output geometry). Cold-start
time (fresh server process, first load, deck.gl chart ready) went from
~9.7s to ~10.3s — essentially flat, not the drop 2_Suitability_Map.py
saw (~13.7s to ~10.3s). Both pages converge to the same ~10.3s now that
neither pays a runtime simplify cost: the remaining time is dominated
by geopandas' GeoJSON parsing of the shared 30MB file plus Streamlit's
own module-import/session overhead, not simplification — this page's
9.7s baseline was already close to that floor since its own tolerance/
default-subzone pass (see above) had already cut its payload well
below 2_Suitability_Map.py's pre-fix size. See docs/methodology.md for
both pages' numbers side by side.
"""

import colorsys
import sqlite3
import sys
from pathlib import Path

import altair as alt
import geopandas
import pandas as pd
import pydeck
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import theme  # noqa: E402
from components import accent_divider, callout, card_css, footer, label_chart, metric_row, set_aria_label, sr_only  # noqa: E402

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
DEFAULT_SUBZONE = "Pongakawa"


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

    # Geometry arrives pre-simplified/rounded — see module docstring.
    parcels = geopandas.read_file(PARCELS_PATH, columns=["source_id", "parcel_id", "geometry"])

    merged = parcels.merge(candidates, on="source_id", how="inner")
    merged["fill_color"] = merged["lcdb_class_2023"].map(LCDB_COLORS)
    # LCDB_COLORS is a hardcoded list confirmed live against the data at
    # build time (see module docstring). If a future data refresh ever
    # introduces a class not in that list, .map() leaves fill_color as
    # NaN for those rows — pydeck would receive a null color property
    # rather than a clean crash, so this is a real missing-value edge
    # case, not a hypothetical one. Fall back to a neutral grey instead
    # of leaving it unresolved.
    unmapped = merged["fill_color"].isna()
    if unmapped.any():
        merged.loc[unmapped, "fill_color"] = [[120, 120, 120, 200]] * unmapped.sum()
    return merged


def to_geojson(gdf):
    cols = ["parcel_id", "suitability_score", "lcdb_class_2023", "subzone", "fill_color", "geometry"]
    return gdf[cols].__geo_interface__


st.title("Expansion Candidates")
st.caption(
    "Parcels rated Excellent or Good for soil suitability that are not "
    "already under orchard, vineyard, or perennial-crop production — "
    "candidates for future horticultural expansion."
)
callout(
    "info",
    "Parcels already classified as urban or settlement land are excluded "
    "from this view.",
)

subzone = st.selectbox("Subzone", SUBZONE_OPTIONS, index=SUBZONE_OPTIONS.index(DEFAULT_SUBZONE))
lcdb_class = st.selectbox("LCDB class", LCDB_CLASS_OPTIONS)

accent_divider()

with st.spinner("Loading candidates..."):
    all_candidates = load_candidate_data()

    metric_row([("Candidates (urban/settlement excluded)", f"{len(all_candidates):,}")])

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
        callout(
            "info",
            f"No candidates match “{subzone}” + “{lcdb_class}”. "
            "Try a different combination — most subzones only contain a "
            "handful of the 22 land-cover classes present in the region.",
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
                "style": {"backgroundColor": theme.ACCENT, "color": "white"},
            },
        )

        sr_only(
            f"Map of {len(view):,} expansion candidate parcels in {subzone}, "
            f"coloured by LCDB land-cover class ({lcdb_class}). Use the filters "
            "above to narrow by subzone or class."
        )
        st.pydeck_chart(deck, height=600)
        label_chart("Expansion candidates map")

accent_divider()

# "What kind of land are these mostly?" — a quick composition readout,
# always over the full candidate set (not the current subzone/class
# filters above), placed after the map rather than before it (layout
# order: filters -> KPI -> map -> this chart). Horizontal bars (not
# vertical) because LCDB class names are long ("High Producing Exotic
# Grassland") — vertical bars would force rotated or truncated labels;
# horizontal bars give each name its own full-width row to read normally.
TOP_N_LCDB = 6
lcdb_counts = (
    all_candidates["lcdb_class_2023"]
    .value_counts()
    .head(TOP_N_LCDB)
    .rename_axis("lcdb_class")
    .reset_index(name="count")
)
LCDB_CHART_ORDER = list(lcdb_counts.sort_values("count")["lcdb_class"])
LCDB_CHART_AXIS = alt.Axis(labelColor=theme.CHART_AXIS_COLOR, titleColor=theme.CHART_AXIS_COLOR)
# Vega-Lite's default labelLimit (~180px) truncated the longer LCDB
# class names ("High Producing Exotic Grassland") with an ellipsis —
# confirmed via rendered screenshot, not assumed. Full-length labels
# need real room, so this axis gets its own wider limit instead of
# sharing LCDB_CHART_AXIS with the (short-label) x-axis.
LCDB_Y_AXIS = alt.Axis(labelColor=theme.CHART_AXIS_COLOR, titleColor=theme.CHART_AXIS_COLOR, labelLimit=260)
with st.container(key="lcdb-overview-chart"):
    st.caption(f"Top {TOP_N_LCDB} land-cover classes among all {len(all_candidates):,} candidates:")
    lcdb_bars = alt.Chart(lcdb_counts).mark_bar(color=theme.ACCENT).encode(
        y=alt.Y("lcdb_class:N", sort=LCDB_CHART_ORDER, title=None, axis=LCDB_Y_AXIS),
        x=alt.X("count:Q", title="Candidates", axis=LCDB_CHART_AXIS),
        tooltip=[
            alt.Tooltip("lcdb_class:N", title="LCDB class"),
            alt.Tooltip("count:Q", title="Candidates", format=","),
        ],
    )
    lcdb_labels = alt.Chart(lcdb_counts).mark_text(dx=6, align="left", color=theme.TEXT, fontSize=12).encode(
        y=alt.Y("lcdb_class:N", sort=LCDB_CHART_ORDER),
        x=alt.X("count:Q"),
        text=alt.Text("count:Q", format=","),
    )
    st.altair_chart((lcdb_bars + lcdb_labels).properties(height=280), use_container_width=True)
card_css("lcdb-overview-chart", padding="1rem 1rem 0.5rem")
set_aria_label(
    '.st-key-lcdb-overview-chart [data-testid="stVegaLiteChart"]',
    f"Horizontal bar chart of the top {TOP_N_LCDB} LCDB land-cover classes by candidate count.",
)

footer()
