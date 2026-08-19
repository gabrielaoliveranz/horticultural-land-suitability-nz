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

accent_divider() and footer() now live in components.py (design-system
pass: the same divider language is used on pages 1-5, and every page
shares one footer) — this page imports them rather than defining its
own, so the pattern can't drift out of sync across pages.

Copy pass (corpo tone): "Sister project" -> "Companion", and the "What
makes this different" paragraph dropped the self-referential portfolio
framing ("Most portfolio dashboards run on...") and "public git
history" in favour of plain business language, keeping every factual
claim (the exact 4 issues found and fixed) intact. See the dashboard
polish report for the full before/after text across all 6 pages.

Design-token pass: the accent colour now comes from theme.ACCENT
instead of a locally-defined ACCENT constant — this page's tagline was
the only remaining place still hardcoding it separately.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import theme  # noqa: E402
from components import accent_divider, footer  # noqa: E402


st.title("Terroir")
st.subheader(
    "Geospatial land-suitability analysis for Bay of Plenty kiwifruit horticulture."
)

st.html(
    f'<p style="color:{theme.ACCENT}; font-weight:600; font-size:1.05rem; '
    f'margin-top:-0.5rem;">Real data. Real analysis. No shortcuts.</p>'
)

st.markdown(
    "Companion to [**Apophenia**](https://apophenia-nz.vercel.app), "
    "a kiwifruit export risk simulator — together, they cover both "
    "operational risk and land-level suitability across Bay of Plenty "
    "horticulture."
)

accent_divider()

st.markdown("### What makes this different")
st.markdown(
    "Terroir is built entirely on official, openly licensed data — LINZ "
    "cadastral parcels (Land Information New Zealand), S-map soil data "
    "and LCDB land cover (Manaaki Whenua – Landcare Research), and "
    "Open-Meteo climate records (ERA5 reanalysis) — spatially joined and "
    "scored at the individual parcel level. Every data-quality issue "
    "encountered along the way, including coordinate system mismatches, "
    "a macron-encoding mismatch that silently excluded an entire "
    "district, a non-unique join key, and a scoring boundary error, is "
    "documented and resolved transparently, with a full audit trail in "
    "the project's public repository."
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
#
# Restyled from a plain text link to a real solid-fill button
# (theme.BUTTON_*) — this is the one primary action on the page, and a
# text-only link (even in the accent colour) didn't read as "the" thing
# to click next to a page full of body copy. White-on-ACCENT measures
# 6.19:1 (see theme.py's Buttons section), well past WCAG.
#
# The hover state used to lift on translateY(-2px) with a stronger drop
# shadow underneath. Dropped along with every shadow in the app (see
# theme.py's Surfaces section) — a button floating upward with no
# shadow to justify the lift reads as a rendering bug, not an
# interaction cue. Hover is now a background-colour darken only.
with st.container(key="cta-explore"):
    st.page_link(
        "pages/1_Overview.py",
        label="**Explore the analysis →**",
        icon=":material/query_stats:",
    )
st.html(
    f"""<style>
    .st-key-cta-explore [data-testid="stPageLink"] {{ display: inline-flex; width: auto; min-height: 0; }}
    .st-key-cta-explore a {{
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: {theme.BUTTON_BG} !important;
        color: {theme.BUTTON_TEXT} !important;
        padding: 0.9rem 1.85rem;
        border-radius: {theme.BUTTON_RADIUS};
        font-size: 1.05rem;
        text-decoration: none !important;
        box-shadow: {theme.BUTTON_SHADOW};
        transition: background-color 0.15s ease;
    }}
    .st-key-cta-explore a:hover {{
        background: {theme.BUTTON_BG_HOVER} !important;
    }}
    .st-key-cta-explore a p {{ color: {theme.BUTTON_TEXT} !important; margin: 0; font-weight: 600; }}
    .st-key-cta-explore a span[data-testid="stIconMaterial"] {{ color: {theme.BUTTON_TEXT} !important; }}
    </style>"""
)

footer()
