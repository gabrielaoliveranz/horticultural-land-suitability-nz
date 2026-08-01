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
"""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "terroir.db"


@st.cache_data
def load_climate_data():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql("SELECT * FROM subzone_climate_risk", conn)


st.title("Climate Risk")
st.caption(
    "Frost days, chill hours, and heavy rain days by subzone — see "
    "docs/methodology.md, \"Climate risk ingestion\", for definitions and "
    "thresholds (chill hours: May–August dormancy window; heavy rain: "
    ">25mm days)."
)

df = load_climate_data().sort_values("chill_hours_annual_avg")

st.subheader("Annualized climate metrics, by subzone")
display_df = df.rename(columns={
    "subzone": "Subzone",
    "frost_days_per_year": "Frost days / year",
    "chill_hours_annual_avg": "Chill hours / year (avg)",
    "heavy_rain_days_per_year": "Heavy rain days / year",
})[["Subzone", "Frost days / year", "Chill hours / year (avg)", "Heavy rain days / year"]]
st.dataframe(display_df, hide_index=True, width="stretch")

with st.expander("Raw 10-year totals (for context)"):
    st.caption(
        "Chill hours has no raw-total column here — only the per-year "
        "average is stored."
    )
    raw_df = df.rename(columns={
        "subzone": "Subzone",
        "frost_days": "Frost days (10-year total)",
        "heavy_rain_days": "Heavy rain days (10-year total)",
    })[["Subzone", "Frost days (10-year total)", "Heavy rain days (10-year total)"]]
    st.dataframe(raw_df, hide_index=True, width="stretch")

st.subheader("What stands out")
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
