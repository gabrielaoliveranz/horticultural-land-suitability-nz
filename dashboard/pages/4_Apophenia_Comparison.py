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

The -0.86 caveat below states a number I actually recomputed (Opotiki
excluded: r drops to -0.76 at n=4), not an assumed "one point drives
everything" narrative — that assumption turned out to overstate it:
Opotiki is the extreme/leverage point but the correlation survives
removing it, just weaker.
"""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "terroir.db"


@st.cache_data
def load_comparison_data():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql("SELECT * FROM cross_project_comparison", conn)


st.title("Apophenia Comparison")

st.warning(
    "**Apophenia's corridor risk data is synthetic/illustrative**, generated "
    "for portfolio purposes, not measured operational data (real freight "
    "volumes, real incident logs). This comparison demonstrates cross-project "
    "analytical technique — joining and comparing two related portfolio "
    "projects — **not a validated real-world finding.** n=5 is also far too "
    "small for statistical confidence, regardless of the data's provenance."
)

df = load_comparison_data().sort_values("mean_score", ascending=False)

st.subheader("Terroir (real) vs. Apophenia (synthetic), by subzone")
display_df = df.rename(columns={
    "subzone": "Subzone",
    "mean_score": "Terroir: suitability score (real)",
    "distance_port_km": "Apophenia: distance to port, km (synthetic)",
    "base_risk_weight": "Apophenia: base risk weight (synthetic)",
    "psa_incidence_historical": "Apophenia: PSA incidence (synthetic)",
})
st.dataframe(display_df, hide_index=True, width="stretch")

st.subheader("Correlations: Terroir suitability vs. each Apophenia risk indicator")

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

st.caption(
    f"Caveat on the {r_psa:.2f} figure: Opotiki is the extreme point on both "
    "axes (lowest suitability score, highest PSA incidence, 0.22 vs. "
    "0.09–0.18 for the other four subzones), so it's doing real work in a "
    "5-point correlation. Recomputed without it: r = "
    f"{df[df['subzone'] != 'Opotiki']['mean_score'].corr(df[df['subzone'] != 'Opotiki']['psa_incidence_historical']):.2f} "
    "(n=4) — still a strong negative relationship, just a bit weaker, not a "
    "single point manufacturing the whole result. Either way, n=4-5 is too "
    "small to treat this as more than illustrative."
)
