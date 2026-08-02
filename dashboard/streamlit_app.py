# =============================================================================
# TERROIR — Streamlit dashboard entrypoint
# Script: streamlit_app.py
# Stage:  Dashboard (Fase 5)
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Entrypoint for the Terroir Streamlit dashboard (run via
`streamlit run dashboard/streamlit_app.py`).

Wires up the 6 pages using st.Page + st.navigation — confirmed as the
current recommended multipage pattern (Streamlit >= 1.36), not the older
auto-discovered pages/ directory convention. Page files still live under
pages/ with numbered filenames for human readability, but navigation
order and titles are controlled explicitly here, not inferred from
filenames.

Nav icons use Material Symbols (`:material/name:`), not emoji — per
Streamlit's own design guidance and Impeccable's craft-floor rule
against emoji standing in for an icon system. The browser-tab favicon
below is a single deliberate kiwifruit emoji, not part of that system,
so it's left as-is.

No data-bootstrap step here: data/processed/terroir.db and
parcels_linz.geojson are committed to the repo via Git LFS (see
.gitattributes and data/processed/README.md), so they're present on
disk on every deploy, including a fresh Streamlit Cloud clone — no
ingestion-on-first-load step needed. An earlier version ran the
pipeline live on cold start instead; removed once the data itself
started shipping with the repo.
"""

import streamlit as st

st.set_page_config(
    page_title="Terroir — Bay of Plenty Land Suitability",
    page_icon="🥝",
    layout="wide",
)

pages = [
    st.Page("pages/0_Intro.py", title="Intro", icon=":material/home:", default=True),
    st.Page("pages/1_Overview.py", title="Overview", icon=":material/analytics:"),
    st.Page("pages/2_Suitability_Map.py", title="Suitability Map", icon=":material/map:"),
    st.Page("pages/3_Expansion_Candidates.py", title="Expansion Candidates", icon=":material/trending_up:"),
    st.Page("pages/4_Apophenia_Comparison.py", title="Apophenia Comparison", icon=":material/link:"),
    st.Page("pages/5_Climate_Risk.py", title="Climate Risk", icon=":material/cloud:"),
]

pg = st.navigation(pages)
pg.run()
