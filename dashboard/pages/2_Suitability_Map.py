# =============================================================================
# TERROIR — Suitability Map page
# Script: pages/2_Suitability_Map.py
# Stage:  Dashboard (Fase 5)
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Parcel-level map: geometry from data/processed/parcels_linz.geojson,
joined on source_id with suitability_score and subzone from terroir.db.
Coloured by suitability level (Excellent/Good/Marginal) via a pydeck
GeoJsonLayer, with a subzone filter (5 named Apophenia subzones + "All")
to narrow the view and keep rendering fast.

Only scored parcels are shown (inner join with parcel_scores) —
parcels with no S-map or LCDB match, road/hydro features, and
duplicate legal-title records over the same physical land are all
excluded upstream and simply don't appear here, consistent with
every other scoring page (see docs/methodology.md, "Handling
unmatched parcels (nulls)" and "Physical-parcel grouping").
Functional, minimal styling for now, same as 0_Intro.py /
1_Overview.py.

Level colours (colorblind-safe fix, replacing the original green/gold/
red scheme): an Impeccable accessibility audit ran an actual deuteranopia/
protanopia simulation (via the `colorspacious` library — a real
simulation, not eyeballed) on the original brand-palette fill colours and
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
alpha-blended-over-background colours (not just the raw fill RGB, since
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
lower opacity washes every colour toward the same light grey background,
pulling Good and Marginal closer together, not further apart (Good-
Marginal distance dropped to ~63-68 with graduated opacity vs. ~110-120
with it removed). So opacity is uniform (200) across all three levels,
same as the original scheme, and the secondary non-colour cue is border
line width instead (thin for Excellent, thicker for Marginal) — doesn't
touch hue/opacity at all, so it can't undermine the CVD fix, and gives
WCAG 1.4.1 a genuine second channel beyond colour alone.

This is a deliberate, documented deviation from PRODUCT.md's brand
palette for this one map's data encoding — accessibility on the
flagship page's primary visual signal outweighs brand-palette
consistency here. The rest of the app still uses the confirmed brand
colours; this exception is scoped to LEVEL_COLORS only.

Regression note (caught and fixed before shipping this change): the
first version of the line-width secondary cue blanked both the map AND
its basemap entirely — not a colour problem, a pydeck one. pydeck's
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
coordinate precision than a web map needs at any zoom this page uses.

Simplification moved upstream into src/ingest_linz.py (was: this
page's own load_map_data(), re-simplifying on every cold cache miss —
see that script's own docstring for why and the measured cold-start
numbers this was chasing). parcels_linz.geojson is now the
already-simplified, already-precision-rounded canonical file; this
page just reads it. Same tolerance as before the move (~5m max
deviation, ~11cm precision grid) — see ingest_linz.py for the
Douglas-Peucker guarantee and pixel-resolution math, not repeated here
since it's no longer this page's own derivation to justify.

Performance pass (after the colorblind-fix and crash-guard changes
above were confirmed working):

1. Default subzone changed from "All" to Katikati (271 parcels — small
   without being the single smallest; Opotiki is smaller at 78 but
   isn't a representative first view). Nobody downloads all 21,491
   parcels just by loading the page anymore; "All" is still one click
   away via the selectbox.
2. Audited to_geojson()'s column list against what the layer/tooltip
   actually reference: parcel_id, suitability_score, subzone,
   suitability_level, fill_color, and line_width are each read by
   either the tooltip HTML or a get_*color/get_*width accessor —
   nothing unused was found to drop.

Measured payload sizes (compact JSON, same column set, actual
to_geojson() output — not estimated, pre-simplified file): "All"
18.81MB, Katikati default 187.3KB. Cold-start time (fresh server
process, first load, deck.gl chart ready) dropped from ~13.7s to
~10.3s after moving simplification out of the runtime path — see
docs/methodology.md for the full before/after and the same number
measured for 3_Expansion_Candidates.py.

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

Accessibility pass: pydeck_chart has no native aria-label parameter, so
label_chart() sets role="img"/aria-label directly on its
[data-testid="stDeckGlJsonChart"] wrapper via a small injected script
(confirmed via DOM inspection that it renders in-page, not inside an
iframe — see components.py's label_chart() docstring for the wrong
assumption that was corrected here). A hidden sr_only() text
description sits just above the map too, since the WebGL canvas itself
has no per-parcel content a screen reader can enumerate regardless of
labelling. The expander below gets the same card treatment as the KPI
rows on other pages (card_css) — same fix for the same "flatness"
finding, applied here too since this page has an expander, not KPIs.

Copy pass (corpo tone): dropped "same as elsewhere" (an internal
cross-reference, not something a visitor needs) from the main caption
and replaced it with a plain explanation of why 1,343 parcels are
excluded. Light polish on the scoring explainer's wording.

Design-token pass: the empty-state message now uses callout("info",
...) instead of st.info() — Streamlit's default info box wasn't part
of the confirmed palette either, same reasoning as the warning-box
restyle on 4_Apophenia_Comparison.py.
"""

import sys
from pathlib import Path

import geopandas
import pandas as pd
import pydeck
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "dashboard"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))
import theme  # noqa: E402
from components import accent_divider, callout, card_css, footer, label_chart, sr_only  # noqa: E402
from config import DB_PATH, PARCELS_PATH, get_connection  # noqa: E402

# Same bins/right=False as subzone_summary.py and
# regional_summary_expansion.py — see docs/methodology.md, "Score
# distribution and suitability levels" (the boundary-bug fix).
LEVEL_BINS = [-float("inf"), 5.0, 8.0, float("inf")]
LEVEL_LABELS = ["Marginal", "Good", "Excellent"]

# Colourblind-safe diverging blue -> orange scheme, replacing the
# original green/gold/red brand colours — see module docstring's "Level
# colours" note for the verified deuteranopia/protanopia numbers.
LEVEL_COLORS = {
    "Excellent": [0, 63, 145, 200],     # deep blue
    "Good": [255, 176, 46, 200],        # amber
    "Marginal": [196, 57, 0, 200],      # deep orange
}

# Secondary, non-colour visual cue (WCAG 1.4.1: colour must not be the
# only signal) — border width in pixels, thin to thick as suitability
# drops. Deliberately not opacity: graduated opacity was verified to
# hurt colourblind discriminability against this page's light background
# (see docstring), so it stays uniform and line width carries the
# second channel instead.
LEVEL_LINE_WIDTHS = {
    "Excellent": 0.5,
    "Good": 1.0,
    "Marginal": 2.0,
}

# NAMED_SUBZONES/OUTSIDE_SUBZONES_LABEL mirror
# 3_Expansion_Candidates.py's pattern exactly, for the same reason: some
# scored parcels carry a null subzone (outside the 5 named Apophenia
# subzones), and that group needs its own filterable option rather than
# being invisible/only reachable via "All" — this page was missing it
# while Expansion Candidates already had it, an inconsistency fixed here.
NAMED_SUBZONES = ["Tauranga", "Te Puke", "Pongakawa", "Katikati", "Opotiki"]
OUTSIDE_SUBZONES_LABEL = "Outside the 5 named subzones"
SUBZONE_OPTIONS = ["All", *NAMED_SUBZONES, OUTSIDE_SUBZONES_LABEL]
DEFAULT_SUBZONE = "Katikati"


@st.cache_data
def load_map_data():
    # Geometry arrives pre-simplified and precision-rounded — see module
    # docstring's "Geometry note". This used to be a ~110MB file needing
    # simplify()/set_precision() on every cold cache miss; now it's a
    # ~30MB file, already at map-ready precision, just read and joined.
    parcels = geopandas.read_file(PARCELS_PATH, columns=["source_id", "parcel_id", "geometry"])

    with get_connection(DB_PATH) as conn:
        # parcel_scores already carries subzone (copied at scoring time
        # in calculate_score.py) — no join needed.
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
    "Parcel-level suitability scores, colour-coded by rating. Only parcels "
    "with a complete soil-data match are shown; 1,343 parcels without an "
    "S-map record are excluded from this view."
)

subzone = st.selectbox("Subzone", SUBZONE_OPTIONS, index=SUBZONE_OPTIONS.index(DEFAULT_SUBZONE))

# Spinner wraps only the heavy part — data load + the pydeck render — not
# the title/caption/selectbox above (instant, always interactive) or the
# legend/expander below (static, no data dependency).
with st.spinner("Loading map..."):
    all_parcels = load_map_data()
    if subzone == "All":
        view = all_parcels
    elif subzone == OUTSIDE_SUBZONES_LABEL:
        view = all_parcels[all_parcels["subzone"].isna()]
    else:
        view = all_parcels[all_parcels["subzone"] == subzone]

    st.caption(f"Showing {len(view):,} of {len(all_parcels):,} scored parcels.")

    if len(view) == 0:
        # Same latent bug class as Expansion Candidates — see module
        # docstring's "Empty-state guard" note. Every named subzone
        # currently has scored parcels, so this isn't reachable today,
        # but it gets the same guard rather than relying on that.
        callout("info", f"No scored parcels found for “{subzone}”.")
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
                "style": {"backgroundColor": theme.ACCENT, "color": "white"},
            },
        )

        sr_only(
            f"Map of {len(view):,} parcels in {subzone}, coloured by suitability "
            "level: deep blue for Excellent, amber for Good, deep orange for "
            "Marginal. Hover or use the table view on other pages for exact "
            "scores per parcel."
        )
        st.pydeck_chart(deck, height=600)
        label_chart(f"Suitability map, {subzone}")

# Legend — pydeck has no native in-map legend, so this is a plain
# colour-key row underneath, built from the same LEVEL_COLORS /
# LEVEL_LINE_WIDTHS dicts the map itself uses (single source of truth,
# can't drift out of sync). Swatch border thickness mirrors each
# level's line_width, so the legend documents both visual channels
# (colour and border), not just colour.
legend_swatches = "".join(
    f'<span style="display:inline-flex; align-items:center; margin-right:1.5rem;">'
    f'<span style="display:inline-block; width:14px; height:14px; border-radius:{theme.CARD_RADIUS}; '
    f'background:rgb({r},{g},{b}); border:{LEVEL_LINE_WIDTHS[level] * 1.5}px solid rgba(0,0,0,0.45); '
    f'margin-right:0.4rem;"></span>{level}</span>'
    for level, (r, g, b, _a) in LEVEL_COLORS.items()
)
with st.container(key="map-legend"):
    st.html(f'<div style="display:flex; align-items:center;">{legend_swatches}</div>')
card_css("map-legend", padding="0.85rem 1.25rem")

accent_divider()

with st.expander("How is this score calculated?", key="score-explainer"):
    st.markdown(
        "Each parcel's score (0-10) combines 4 S-map soil factors, each "
        "scored 0-10 and weighted:\n\n"
        "- **Soil order** — 40%\n"
        "- **Soil texture** — 40%\n"
        "- **Soil drainage** — 10%\n"
        "- **Soil depth** — 10%\n\n"
        "Soil order and texture vary significantly across parcels, so they "
        "carry the greatest weight. Drainage and depth are far less varied "
        "region-wide (most parcels are \"Well drained\" and \"Deep\"), so "
        "they carry less.\n\n"
        "**Levels:** Excellent 8.0–10.0 · Good 5.0–7.9 · Marginal below 5.0."
    )
card_css("score-explainer", padding="0.25rem")

footer()
