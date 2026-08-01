# =============================================================================
# TERROIR — Intro page
# Script: pages/0_Intro.py
# Stage:  Dashboard (Fase 5)
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Landing page for the Terroir dashboard — full build, not a placeholder.
One-line description, a link to Apophenia as sister project, the real
differentiator (drawn from PRODUCT.md's Positioning section), and a
prominent link into Overview.

Typography-led, no stock imagery. Uses the confirmed candidate palette
from PRODUCT.md ("Brand Commitments") as a single accent colour, with
straight-line accent-coloured rules marking section breaks — not
Streamlit's default grey st.divider(), and not diagonal cuts (explicitly
ruled out as reading like consumer marketing, e.g. Zespri's own site).
See PRODUCT.md, "Product Principles" ("credibility over spectacle").
"""

import streamlit as st

# Mirrors [theme] primaryColor in .streamlit/config.toml — that file is
# the source of truth for the confirmed palette; kept in sync here only
# because the tagline/divider below are custom HTML that Streamlit's
# native theming doesn't reach.
ACCENT = "#0B4F3D"


def accent_divider():
    """Subtle straight-line rule in the accent colour, replacing st.divider()."""
    st.html(
        f'<hr style="border:none; border-top:1px solid {ACCENT}; '
        f'opacity:0.35; margin:1.75rem 0;">'
    )


st.title("Terroir")
st.subheader(
    "Geospatial land-suitability analysis for Bay of Plenty kiwifruit horticulture."
)

st.html(
    f'<p style="color:{ACCENT}; font-weight:600; font-size:1.05rem; '
    f'margin-top:-0.5rem;">Real data. Real analysis. No shortcuts.</p>'
)

st.markdown(
    "Sister project to [**Apophenia**](https://apophenia-nz.vercel.app), "
    "a kiwifruit export risk simulator — together they cover both "
    "operational risk and land-level suitability for Bay of Plenty "
    "horticulture."
)

accent_divider()

st.markdown("### What makes this different")
st.markdown(
    "Most portfolio dashboards run on synthetic or Kaggle-style data. "
    "Terroir is built entirely on real official New Zealand government "
    "sources — LINZ cadastral parcels, S-map soil data, LCDB land cover, "
    "and Open-Meteo climate records — spatially joined and scored at the "
    "individual parcel level. Every real data-quality issue found along "
    "the way (coordinate system mismatches, macron-spelling gaps, a "
    "non-unique join key, a scoring boundary bug) is disclosed and fixed "
    "in the open, in the public git history, rather than smoothed over "
    "for a cleaner story."
)

accent_divider()

# st.page_link takes no `key` parameter (confirmed against its actual
# signature after a first attempt crashed the app), so the CSS-targeting
# container comes from wrapping it in st.container(key=...) instead.
# st.page_link also ignores both primaryColor and linkColor from
# .streamlit/config.toml (confirmed by testing — renders browser-default
# #0000EE regardless) and exposes no colour parameter of its own. This
# is the documented exception where targeted CSS is warranted: no native
# mechanism reaches this widget's link colour.
with st.container(key="cta-explore"):
    st.page_link(
        "pages/1_Overview.py",
        label="**Explore the analysis →**",
        icon=":material/query_stats:",
    )
st.html(f'<style>.st-key-cta-explore a {{ color: {ACCENT} !important; }}</style>')
