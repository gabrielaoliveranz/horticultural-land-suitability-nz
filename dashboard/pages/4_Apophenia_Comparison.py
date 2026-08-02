# =============================================================================
# TERROIR — Apophenia Comparison page
# Script: pages/4_Apophenia_Comparison.py
# Stage:  Dashboard (Fase 5)
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Business question 3: does Apophenia's operational risk correlate with
Terroir's soil suitability? Loads cross_project_comparison (5 rows, one
per named subzone: mean_score from Terroir's real scoring, plus
distance_port_km/base_risk_weight/psa_incidence_historical from
Apophenia's synthetic corridor data) from terroir.db.

No spinner: this is a 5-row query, not a map — the CLAUDE.md rule
requiring a spinner applies to map pages specifically.

Correlations are computed live from the loaded table (pandas .corr()),
not hardcoded, so this page can't silently drift out of sync with
whatever's actually in the table.

The real-vs-synthetic disclaimer is the point of this page, not an
afterthought — see PRODUCT.md's Capabilities and Constraints ("this
caveat must stay visibly attached to that result wherever it's shown")
and docs/methodology.md, "Cross-project comparison (business question
3)". Rendered as st.warning(), not a footnote.

The -0.85 caveat below states a number I actually recomputed (Opotiki
excluded: r drops to -0.76 at n=4), not an assumed "one point drives
everything" narrative — that assumption turned out to overstate it:
Opotiki is the extreme/leverage point but the correlation survives
removing it, just weaker. (This was -0.86 before src/01_ingest_linz.py's
geometry-simplification move shifted Opotiki's mean_score by a
centroid-boundary flip — see docs/methodology.md's "Geometry
simplification moved to ingestion" section; the correlation itself is
computed live from the loaded table below, not hardcoded, so the
displayed number was never stale, only this docstring's description of
it.)

Design-system pass: shared accent_divider()/footer() from components.py,
one divider between the comparison table and the correlations section
(the page's one clear content-type boundary), same as every other page.

Second design-audit pass (tables): st.dataframe defaults to left-
aligning every column regardless of content type. column_config now
right-aligns the 4 numeric columns and left-aligns Subzone explicitly
(not relying on the default), plus a consistent 2-decimal format on the
3 Apophenia columns — the raw data mixes 1 and 2 decimal places
(0.2 vs. 0.18), which read as inconsistent precision even though
they're not. Deliberately not centred/justified text — left-aligned
text with right-aligned numbers is the standard, more readable
convention for tabular data, per the earlier discussion.

Copy pass (corpo tone): the disclaimer and the Opotiki caveat both used
statistical shorthand ("n=5", "n=4-5", "5-point correlation") and the
word "provenance" — replaced with plain business language ("five
subzones", "a small comparison set") that states the same limitation
without the jargon. Every number (0.22, 0.09-0.18, the recomputed r)
is unchanged — this was a wording pass, not a substance change.

Design-token pass: st.warning() replaced with callout("warning", ...).
Streamlit's default warning styling is a mustard yellow that isn't part
of the confirmed palette and doesn't match anything else in the app —
a contrast audit also found it borderline-failing WCAG (4.48:1 against
the 4.5:1 minimum, measured from the actual rendered colours, not
assumed adequate). callout("warning", ...) uses SunGold gold as a tint
+ border accent with TEXT (not the accent) as the message colour,
verified to pass with wide margin (13:1+) instead of being right at
the edge.
"""

import sqlite3
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import theme  # noqa: E402
from components import accent_divider, callout, card_css, footer, section_header, set_aria_label  # noqa: E402

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "terroir.db"


@st.cache_data
def load_comparison_data():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql("SELECT * FROM cross_project_comparison", conn)


st.title("Apophenia Comparison")

callout(
    "warning",
    "**Apophenia's corridor risk figures are synthetic, illustrative "
    "estimates** — not measured operational data such as real freight "
    "volumes or incident logs. This comparison demonstrates cross-project "
    "analytical technique, joining two related datasets, **not a validated "
    "real-world finding.** With only five subzones in the comparison, the "
    "results should be read as directional, not statistically conclusive.",
)

df = load_comparison_data().sort_values("mean_score", ascending=False)

section_header("Terroir (real) vs. Apophenia (synthetic), by subzone")
display_df = df.rename(columns={
    "subzone": "Subzone",
    "mean_score": "Terroir: suitability score (real)",
    "distance_port_km": "Apophenia: distance to port, km (synthetic)",
    "base_risk_weight": "Apophenia: base risk weight (synthetic)",
    "psa_incidence_historical": "Apophenia: PSA incidence (synthetic)",
})
st.dataframe(
    display_df,
    hide_index=True,
    width="stretch",
    column_config={
        "Subzone": st.column_config.TextColumn(alignment="left"),
        "Terroir: suitability score (real)": st.column_config.NumberColumn(
            alignment="right", format="%.2f"
        ),
        "Apophenia: distance to port, km (synthetic)": st.column_config.NumberColumn(
            alignment="right", format="%d km"
        ),
        "Apophenia: base risk weight (synthetic)": st.column_config.NumberColumn(
            alignment="right", format="%.2f"
        ),
        "Apophenia: PSA incidence (synthetic)": st.column_config.NumberColumn(
            alignment="right", format="%.2f"
        ),
    },
)

accent_divider()

section_header("Correlations: Terroir suitability vs. each Apophenia risk indicator")

r_distance = df["mean_score"].corr(df["distance_port_km"])
r_risk = df["mean_score"].corr(df["base_risk_weight"])
r_psa = df["mean_score"].corr(df["psa_incidence_historical"])

st.markdown(
    f"- **Distance to port** — r = {r_distance:.2f}. Moderate negative "
    "relationship: subzones farther from the port tend to score somewhat "
    "lower on soil suitability.\n"
    f"- **Base risk weight** — r = {r_risk:.2f}. **No meaningful "
    "relationship** — essentially uncorrelated with soil suitability.\n"
    f"- **Historical PSA incidence** — r = {r_psa:.2f}. Strong negative "
    "relationship: subzones with more historical PSA incidents tend to "
    "score lower on soil suitability. See caveat below."
)

st.caption("Same relationships, visualised — colour tracks subzone, dashed line: linear trend:")

# Scatter, not another table: the r values above are numbers; these
# make the actual shape of each relationship (and Opotiki's leverage on
# the PSA one — see the caveat below) visually inspectable. Same
# suitability score on the y-axis across all 3, one Apophenia indicator
# per x-axis. Stacked full-width (one per row) rather than 3 cramped
# columns — the same layout fix as 5_Climate_Risk.py's charts, for the
# same reason: 3 columns in this app's ~736px content area left each
# panel too narrow to read comfortably.
#
# Points are coloured by subzone (not a single flat colour) so the same
# subzone can be visually tracked across all 3 panels — e.g. Opotiki's
# position as the low-suitability/high-PSA outlier (see the caveat
# below) is now a colour you can follow from chart to chart, not just a
# label you'd have to hover to find each time. Palette is Okabe-Ito
# derived, not the app's own ACCENT (a single hue can't encode 5
# categories) — verified under simulated deuteranomaly/protanomaly the
# same way LEVEL_COLORS was on the map pages: worst-case pairwise
# distance 103.0 (vs. the ~50-60 threshold generally considered
# reliably distinguishable, and comfortably in the same range as the
# map's own 110.1). A thin dark stroke is added to every point — the
# yellow slice of this palette measures only 1.32:1 against the white
# card background on its own (checked, not assumed fine just because
# CVD-safe), so fill alone isn't enough to keep it visible here.
SUBZONE_COLORS = {
    "Tauranga": "#0072B2",
    "Te Puke": "#D55E00",
    "Pongakawa": "#009E73",
    "Katikati": "#56B4E9",
    "Opotiki": "#F0E442",
}
SCATTER_AXIS = alt.Axis(labelColor=theme.CHART_AXIS_COLOR, titleColor=theme.CHART_AXIS_COLOR)
SCATTER_METRICS = [
    ("distance_port_km", "Distance to port (km)", r_distance, "scatter-distance"),
    ("base_risk_weight", "Base risk weight", r_risk, "scatter-risk"),
    ("psa_incidence_historical", "PSA incidence (historical)", r_psa, "scatter-psa"),
]

for field, label, r, key in SCATTER_METRICS:
    with st.container(key=key):
        points = alt.Chart(df).mark_circle(size=160, opacity=0.9, stroke=theme.rgba(theme.TEXT, 0.35), strokeWidth=1).encode(
            x=alt.X(f"{field}:Q", title=label, axis=SCATTER_AXIS),
            y=alt.Y("mean_score:Q", title="Suitability score", axis=SCATTER_AXIS),
            color=alt.Color(
                "subzone:N",
                scale=alt.Scale(domain=list(SUBZONE_COLORS.keys()), range=list(SUBZONE_COLORS.values())),
                legend=alt.Legend(title="Subzone", orient="right"),
            ),
            tooltip=[
                alt.Tooltip("subzone:N", title="Subzone"),
                alt.Tooltip(f"{field}:Q", title=label, format=".2f"),
                alt.Tooltip("mean_score:Q", title="Suitability score", format=".2f"),
            ],
        )
        trend = points.transform_regression(field, "mean_score").mark_line(
            strokeDash=[4, 3],
        ).encode(color=alt.value(theme.rgba(theme.ACCENT, 0.5)))
        scatter_chart = (points + trend).properties(
            height=320,
            title=alt.TitleParams(f"r = {r:.2f}", color=theme.CHART_AXIS_COLOR, fontSize=13, anchor="start"),
        )
        st.altair_chart(scatter_chart, use_container_width=True)
    card_css(key, padding="1rem 1rem 0.5rem")
    set_aria_label(
        f'.st-key-{key} [data-testid="stVegaLiteChart"]',
        f"Scatter plot of suitability score vs. {label.lower()}, coloured by subzone, correlation r = {r:.2f}.",
    )

st.caption(
    f"A note on this figure: Opotiki is an outlier on both measures (the "
    "lowest suitability score and the highest PSA incidence rate, 0.22 "
    "versus 0.09–0.18 for the other four subzones), so it carries "
    "significant weight in a small comparison set. Recalculated without "
    "Opotiki, the relationship remains strong ("
    f"{df[df['subzone'] != 'Opotiki']['mean_score'].corr(df[df['subzone'] != 'Opotiki']['psa_incidence_historical']):.2f}"
    ") — weaker, but not dependent on a single data point. With only four "
    "to five subzones either way, this result should be treated as "
    "illustrative rather than statistically robust."
)

footer()
