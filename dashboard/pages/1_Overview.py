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
"""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "terroir.db"
LEVEL_ORDER = ["Excellent", "Good", "Marginal"]


@st.cache_data
def load_overview_data():
    with sqlite3.connect(DB_PATH) as conn:
        levels = pd.read_sql("SELECT * FROM suitability_levels_summary", conn)
        n_scored = pd.read_sql("SELECT COUNT(*) AS n FROM parcel_scores", conn).iloc[0, 0]
        n_ingested = pd.read_sql("SELECT COUNT(*) AS n FROM parcel_attributes", conn).iloc[0, 0]
    levels = levels.set_index("suitability_level").loc[LEVEL_ORDER].reset_index()
    return levels, int(n_scored), int(n_ingested)


levels, n_scored, n_ingested = load_overview_data()
excellent_pct = levels.loc[levels["suitability_level"] == "Excellent", "pct"].iloc[0]

st.title("Overview")
st.caption("Region-wide suitability breakdown across all 4 target territorial authorities.")

with st.container(horizontal=True):
    st.metric("Parcels ingested", f"{n_ingested:,}")
    st.metric("Parcels scored", f"{n_scored:,}")
    st.metric("% Excellent", f"{excellent_pct:.1f}%")

st.subheader("Suitability levels, region-wide")
st.bar_chart(
    levels,
    x="suitability_level",
    y="parcel_count",
    x_label="",
    y_label="Parcels",
)
