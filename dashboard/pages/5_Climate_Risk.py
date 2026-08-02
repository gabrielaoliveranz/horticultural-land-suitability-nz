# =============================================================================
# TERROIR — Climate Risk page
# Script: pages/5_Climate_Risk.py
# Stage:  Dashboard (Fase 5)
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Business question 5: climate risk profile by subzone. Loads
subzone_climate_risk (5 rows, one per named subzone) from terroir.db —
see docs/methodology.md, "Climate risk ingestion", for how frost days,
chill hours, and heavy rain days were derived.

No spinner: this is a 5-row query, not a map — the CLAUDE.md rule
requiring a spinner applies to map pages specifically.

chill_hours_annual_avg has no raw 10-year-total counterpart in the
table (unlike frost_days and heavy_rain_days, which are each stored as
both a raw 10-year total and a per-year figure) — the raw totals
section below only shows the two columns that actually exist.

The "coastal vs. inland" framing in the interpretation is grounded in
the subzones' own lat/lon (also in this table) and known Bay of Plenty
geography, not asserted from the chill-hour numbers alone: Katikati,
Tauranga, and Opotiki sit on the coast/harbour, while Te Puke and
Pongakawa are inland hill-country kiwifruit country. That split lines
up with the chill-hour numbers themselves (coastal three: 208–283
hours; inland two: 435–451 hours) — the numbers and the geography
corroborate each other rather than one being invented to fit the
other. Phrased as "consistent with," not a precise measured
distance-to-coast claim, since no such measurement exists in the data.

Design-system pass: shared accent_divider()/footer()/card_css() from
components.py. One divider between the raw-totals expander and "What
stands out" (data presentation vs. interpretation is this page's
clearest section boundary); the expander gets the same card treatment
as the score explainer on 2_Suitability_Map.py.

Second design-audit pass (tables): both tables get explicit column_config
— Subzone left-aligned, every numeric column right-aligned with a
consistent decimal format, instead of st.dataframe's default (every
column left-aligned regardless of content type).

Copy pass (corpo tone): dropped the "see docs/methodology.md" internal
reference from the intro caption (the precise thresholds it pointed to
are now stated inline instead), and replaced database-flavoured wording
("no raw-total column", "is stored") in the expander caption with plain
business language.

Design-token pass: "What stands out" is now wrapped in the same
elevated card as the raw-totals expander (card_css) — this page was
flagged as visually flat, and giving the interpretation section its
own surface (distinct from the plain page background the bullets sat
directly on before) gives it presence as a distinct "insight" block,
using the existing card token rather than a new one-off treatment.
"""

import sqlite3
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import theme  # noqa: E402
from components import accent_divider, card_css, footer, section_header, set_aria_label  # noqa: E402

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "terroir.db"


@st.cache_data
def load_climate_data():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql("SELECT * FROM subzone_climate_risk", conn)


st.title("Climate Risk")
st.caption(
    "Frost days, chill hours, and heavy rain days by subzone. Chill hours "
    "are measured across the May–August dormancy window; heavy rain days "
    "are those exceeding 25mm of rainfall."
)

df = load_climate_data().sort_values("chill_hours_annual_avg")

section_header("Annualised climate metrics, by subzone")
display_df = df.rename(columns={
    "subzone": "Subzone",
    "frost_days_per_year": "Frost days / year",
    "chill_hours_annual_avg": "Chill hours / year (avg)",
    "heavy_rain_days_per_year": "Heavy rain days / year",
})[["Subzone", "Frost days / year", "Chill hours / year (avg)", "Heavy rain days / year"]]
st.dataframe(
    display_df,
    hide_index=True,
    width="stretch",
    column_config={
        "Subzone": st.column_config.TextColumn(alignment="left"),
        "Frost days / year": st.column_config.NumberColumn(alignment="right", format="%.1f"),
        "Chill hours / year (avg)": st.column_config.NumberColumn(alignment="right", format="%.1f"),
        "Heavy rain days / year": st.column_config.NumberColumn(alignment="right", format="%.1f"),
    },
)

st.caption("Same metrics, visualised — shade intensity tracks relative risk within each chart:")

# One bar chart per metric, stacked full-width rather than 3 cramped
# columns — the earlier 3-column layout (~220px each in a ~736px
# content area) forced Vega-Lite's label-overlap resolution to drop 3
# of 5 x-axis labels (kept only the first/last), which combined with
# 4 of 5 subzones genuinely having ~0 frost days (invisible bars at
# 0 height) made the frost chart look like only 2 of 5 subzones were
# even present. Neither was a data bug — confirmed via the rendered
# DOM: all 5 subzones' bars and values were always in the chart spec
# (aria-label per bar read "subzone: Katikati; Frost days / year: 0"
# etc. for all 5), just not legible at that width. Full width fixes
# the label collision outright; the text-label layer below (every
# bar gets its numeric value printed above it) makes even a
# genuinely-zero bar legible without relying on bar height at all.
#
# The 3 metrics still don't share a y-axis (frost days ~0-0.2, chill
# hours ~200-450, heavy rain days ~17-24 — one axis would flatten
# frost days to an invisible sliver), so this stays 3 separate charts,
# just stacked instead of side-by-side. Same subzone order
# (SUBZONE_ORDER, matching the table's own chill-hours-ascending sort)
# across all 3 so they stay directly comparable top-to-bottom.
SUBZONE_ORDER = list(df["subzone"])
CHART_AXIS = alt.Axis(labelAngle=0, labelColor=theme.CHART_AXIS_COLOR, titleColor=theme.CHART_AXIS_COLOR)
CHART_Y_AXIS = alt.Axis(labelColor=theme.CHART_AXIS_COLOR, titleColor=theme.CHART_AXIS_COLOR)

# Relative-risk shading: each bar's shade is driven by its own value,
# light terracotta (lowest in that metric) to full-strength ACCENT
# (highest) — meaningful colour, not a flat decorative fill. Domain is
# per-metric (Vega-Lite's default field-driven scale, min/max of that
# one column), so "darkest" always means "highest within this metric,"
# not some shared cross-metric scale that would make Katikati's 0 chill
# hours look identical to its 0 frost days. Chill hours is the one
# metric here where "higher" is agronomically favourable, not risk in
# the literal sense (see module docstring) — shaded the same way as
# the other two anyway, for one consistent visual language across all
# 3 panels, not because higher chill hours is actually worse.
CHART_COLOR_RANGE = [theme.rgba(theme.ACCENT, 0.22), theme.ACCENT]

CLIMATE_METRICS = [
    ("frost_days_per_year", "Frost days / year", "frost-chart"),
    ("chill_hours_annual_avg", "Chill hours / year (avg)", "chill-chart"),
    ("heavy_rain_days_per_year", "Heavy rain days / year", "rain-chart"),
]

for field, label, key in CLIMATE_METRICS:
    with st.container(key=key):
        bars = alt.Chart(df).mark_bar().encode(
            x=alt.X("subzone:N", sort=SUBZONE_ORDER, title=None, axis=CHART_AXIS),
            y=alt.Y(f"{field}:Q", title=label, axis=CHART_Y_AXIS),
            color=alt.Color(f"{field}:Q", scale=alt.Scale(range=CHART_COLOR_RANGE), legend=None),
            tooltip=[
                alt.Tooltip("subzone:N", title="Subzone"),
                alt.Tooltip(f"{field}:Q", title=label, format=".1f"),
            ],
        )
        # Value labels above every bar — the fix for zero-value bars
        # being invisible: a "0.0" text label is legible regardless of
        # bar height, so every subzone reads clearly even when its bar
        # doesn't.
        value_labels = alt.Chart(df).mark_text(dy=-8, color=theme.TEXT, fontSize=12).encode(
            x=alt.X("subzone:N", sort=SUBZONE_ORDER),
            y=alt.Y(f"{field}:Q"),
            text=alt.Text(f"{field}:Q", format=".1f"),
        )
        metric_chart = (bars + value_labels).properties(height=320)
        st.altair_chart(metric_chart, use_container_width=True)
    card_css(key, padding="1rem 1rem 0.5rem")
    set_aria_label(
        f'.st-key-{key} [data-testid="stVegaLiteChart"]',
        f"Bar chart of {label.lower()} by subzone, shaded by relative value within this metric.",
    )

with st.expander("Raw 10-year totals (for context)", key="raw-totals"):
    st.caption(
        "Chill hours are only available as an annual average; a 10-year "
        "total isn't tracked separately."
    )
    raw_df = df.rename(columns={
        "subzone": "Subzone",
        "frost_days": "Frost days (10-year total)",
        "heavy_rain_days": "Heavy rain days (10-year total)",
    })[["Subzone", "Frost days (10-year total)", "Heavy rain days (10-year total)"]]
    st.dataframe(
        raw_df,
        hide_index=True,
        width="stretch",
        column_config={
            "Subzone": st.column_config.TextColumn(alignment="left"),
            "Frost days (10-year total)": st.column_config.NumberColumn(alignment="right", format="%d"),
            "Heavy rain days (10-year total)": st.column_config.NumberColumn(alignment="right", format="%d"),
        },
    )
card_css("raw-totals", padding="0.25rem")

accent_divider()

section_header("What stands out")
with st.container(key="insights-card"):
    st.markdown(
        "- **Frost is a non-issue across the board.** Four of five subzones show "
        "exactly 0.0 frost days/year; Te Puke shows 0.2 — effectively zero. "
        "Consistent with the region's low-elevation, coastal-influenced climate: "
        "frost risk isn't a differentiator between these subzones.\n"
        "- **Chill hours vary a lot, and the split tracks coastal vs. inland "
        "geography.** Katikati (208.4) and Tauranga (338.8) — both directly on "
        "the coast/harbour — sit at the low end; Opotiki (282.6), also coastal, "
        "sits in between. Te Puke (434.7) and Pongakawa (450.7) — inland "
        "hill-country kiwifruit land — run noticeably higher, consistent with "
        "less maritime moderation of overnight temperatures. This matters "
        "agronomically: kiwifruit needs enough chill hours to break dormancy "
        "reliably, so the inland subzones are better placed on this metric "
        "specifically, even though it's not part of the soil suitability score "
        "itself.\n"
        "- **Opotiki stands out on heavy rain frequency.** 23.3 days/year "
        "with >25mm rainfall, clearly above the other four (17.5–19.7). Worth "
        "flagging as an operational risk factor (erosion, access, harvest "
        "timing) distinct from the soil-suitability picture on the other pages."
    )
card_css("insights-card")

footer()
