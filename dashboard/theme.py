# =============================================================================
# TERROIR — Design tokens
# Script: theme.py
# Stage:  Dashboard (Fase 5)
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Single source of truth for every derived visual value in the dashboard —
card style, divider style, callout/alert style, hover style, chart
colours. The only "invented" literals are the hex colours confirmed in
PRODUCT.md's "Brand Commitments" (ACCENT, PRIMARY_GREEN, LIMA_GREEN,
SUNGOLD_GOLD, ALERT_RED, BACKGROUND) plus TEXT (see its own note below).
Everything else — surfaces, borders, shadows, hover tints, callout variants — is
computed from those via explicit alpha blending, not eyeballed, and
lives in exactly one place instead of being redefined page-by-page.

Colour-role rule (see PRODUCT.md's "Brand Commitments" for the same
rule stated in one place, not just here): ACCENT (terracotta) is
general Terroir UI/interaction — buttons, CTA, dividers, section
headers, links, hover states, the back-to-top button, the footer's
Project icons (Apophenia/GitHub/LinkedIn alike, no per-icon colour
distinction) — everywhere a brand accent renders. PRIMARY_GREEN is not
used anywhere in the general UI; an earlier version reserved it
exclusively for the Apophenia footer link's hover state (signalling
"leaves this project"), dropped per direct feedback in favour of one
consistent accent across all three icons. It stays defined below only
as the confirmed-palette reference value from PRODUCT.md, not because
anything renders with it. SUNGOLD_GOLD is warning/callout only
(theme.CALLOUTS["warning"] — Apophenia Comparison's synthetic-data
disclaimer is the one place that shows up). None of this touches
2_Suitability_Map.py's / 3_Expansion_Candidates.py's LEVEL_COLORS: that
blue/amber/deep-orange scheme was specifically verified against a
deuteranopia/protanopia simulation (see that page's own docstring) and
is a separate, accessibility-driven system, not a brand-accent choice.

This module holds only token *values* (colours, spacing, shadows) and
small pure-Python derivation helpers — no Streamlit calls, no rendering.
components.py imports these tokens and does the actual rendering; that
split is deliberate, so "what are the values" and "how do they render"
don't live in the same 200-line file.
"""

# ---- Base palette — PRODUCT.md "Brand Commitments" ------------------------
# ACCENT was proposed at #B5651D ("terracotta"). Checked the same way
# every other colour here is checked, before locking it in — and it
# failed: white text on #B5651D measures 4.34:1 (needs 4.5:1), and
# #B5651D as text directly on BACKGROUND measures 3.53:1 (same
# requirement). Both matter: white-on-ACCENT is the button/CTA case,
# ACCENT-as-text-on-BACKGROUND is the Intro tagline/KPI-value case.
# Darkened via blend(base, "#000000", 0.8) — the same "darken toward
# black" move used for BUTTON_BG_HOVER below — until both cleared 4.5:1
# with real margin rather than barely: #915117 measures 6.19:1 (white
# text on it) and 5.03:1 (as text on BACKGROUND). Still unmistakably
# the same terracotta/burnt-sienna hue, just deep enough to read as
# text-safe, the same tradeoff the old PRIMARY_GREEN's own deep shade made.
ACCENT = "#915117"

# Palette reference only — not used anywhere in the rendered UI. This
# is the original brand green (theme.ACCENT's predecessor as the
# general accent, and briefly the Apophenia footer link's own colour
# after that — both roles have since moved to ACCENT). Kept defined so
# PRODUCT.md's confirmed 5-colour palette still has a live Python value
# to point at, not because any component references it. Contrast, for
# the record: white text on it measures 9.55:1.
PRIMARY_GREEN = "#0B4F3D"
LIMA_GREEN = "#A8C93A"
SUNGOLD_GOLD = "#F2A900"
ALERT_RED = "#C0392B"
BACKGROUND = "#E8E8E3"

# Contrast-safe near-black text. Originally left at Streamlit's default
# (#31333F) as an unconfirmed-but-safe choice — a comprehensive contrast
# audit found that default fails WCAG for st.dataframe's canvas-rendered
# column headers (3.59:1, measured directly from rendered pixels, not
# assumed — CSS can't reach canvas content, so this couldn't be fixed
# with an override and had to be fixed at the theme-token level
# instead). Header text renders at ~60% opacity of this value blended
# over its own near-white header background (empirically derived by
# measuring two different textColor values and solving for the blend
# ratio — see .streamlit/config.toml's own note for the full numbers).
# #14151A is deep enough that the blended header clears 4.5:1 with
# margin (measured 4.63:1) while staying the same neutral-slate family
# as the original, not a different hue. Set as [theme] textColor in
# .streamlit/config.toml (the actual global effect) and mirrored here
# so components.py doesn't hardcode it separately.
TEXT = "#14151A"


def _hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def rgba(hex_color, alpha):
    """Explicit alpha-blend helper — every derived token below goes
    through this rather than a hand-picked hex value."""
    r, g, b = _hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha})"


def blend(hex_fg, hex_bg, alpha):
    """Flattens hex_fg-at-alpha over hex_bg into an opaque hex colour —
    used where a tool (e.g. Vega-Lite's SVG text fill, or anywhere an
    rgba() isn't accepted) needs a solid colour, not a translucent one.
    """
    fr, fg_, fb = _hex_to_rgb(hex_fg)
    br, bg_, bb = _hex_to_rgb(hex_bg)
    r = round(fr * alpha + br * (1 - alpha))
    g = round(fg_ * alpha + bg_ * (1 - alpha))
    b = round(fb * alpha + bb * (1 - alpha))
    return "#%02X%02X%02X" % (r, g, b)


# ---- Text ------------------------------------------------------------------
TEXT_MUTED = rgba(TEXT, 0.62)

# Chart axis/tick label colour: Vega-Lite's own default grey measured at
# 3.02:1 against BACKGROUND — a real WCAG failure (confirmed via DOM
# scan, not assumed), not just aesthetically flat. This is a muted grey
# deliberately quieter than full TEXT (axis labels are supporting
# content, not body text), computed to clear 4.5:1 with margin
# (verified 5.44:1) rather than picked freehand.
CHART_AXIS_COLOR = "#5A5C62"

# ---- Surfaces ----------------------------------------------------------
CARD_BG = "#FFFFFF"
CARD_BORDER = f"1px solid {rgba(ACCENT, 0.12)}"
CARD_SHADOW = f"0 2px 10px {rgba(ACCENT, 0.10)}, 0 1px 2px {rgba(ACCENT, 0.06)}"
# Stronger two-layer shadow for the KPI-card hover lift — same shape as
# CARD_SHADOW (tight layer + soft diffuse layer), just deeper, so a
# hovered card reads as physically closer rather than just "different".
CARD_SHADOW_HOVER = f"0 8px 20px {rgba(ACCENT, 0.16)}, 0 2px 6px {rgba(ACCENT, 0.10)}"
CARD_RADIUS = "12px"

DIVIDER_COLOR = ACCENT
DIVIDER_OPACITY = 0.35

HOVER_TINT = rgba(ACCENT, 0.12)

# ---- Interactive controls (selectboxes, etc.) ---------------------------
# Streamlit's own selectbox renders its bordered "box" with
# border:1px solid BACKGROUND and background:BACKGROUND — i.e. a border
# the same colour as what's behind it, invisible by construction
# (confirmed via computed style before writing these, not assumed).
# These tokens give it a real surface: same white CARD_BG as cards, a
# visible-but-quiet border, a slightly stronger one on hover, and a
# focus ring on the standard "halo" pattern (a soft glow at higher
# alpha), all derived from ACCENT.
INPUT_BG = CARD_BG
INPUT_BORDER = rgba(ACCENT, 0.28)
INPUT_BORDER_HOVER = rgba(ACCENT, 0.5)
INPUT_FOCUS_RING = f"0 0 0 3px {rgba(ACCENT, 0.18)}"

# ---- Buttons -------------------------------------------------------------
# Solid-fill primary action, for the one CTA that should read as "the"
# button on a page (0_Intro.py's "Explore the analysis"). White text on
# ACCENT measures 6.19:1; on the hover shade, 7.77:1 — both verified,
# not assumed safe just because the colour reads as dark.
BUTTON_BG = ACCENT
BUTTON_TEXT = "#FFFFFF"
BUTTON_BG_HOVER = blend(ACCENT, "#000000", 0.85)  # ~15% darker
BUTTON_SHADOW = f"0 4px 14px {rgba(ACCENT, 0.28)}"

# ---- Callout/alert variants -------------------------------------------
# Each callout pairs a light tint of one accent colour (background) with
# a full-strength left-border accent bar, and TEXT (never the accent
# itself) as body text — several accents in the confirmed palette fail
# WCAG as text (SunGold gold 1.63:1, lima green 1.54:1 against
# BACKGROUND), so using them for tints/borders only and TEXT for the
# actual message is the same rule already established for map fills.
#
# Mapping: "info" uses ACCENT (the brand's neutral home colour, already
# carrying dividers/links/cards — no dedicated blue exists in the
# confirmed palette, and introducing an unconfirmed one would be an
# unrequested brand decision). "warning" uses SunGold gold, the
# semantically closest confirmed colour to "caution". "danger" uses
# alert red. Lima green isn't used here — no page currently needs a
# fourth ("success") variant, and forcing one in just to use every
# palette colour would be decoration for its own sake.
CALLOUTS = {
    "info": {"accent": ACCENT, "bg": rgba(ACCENT, 0.07)},
    "warning": {"accent": SUNGOLD_GOLD, "bg": rgba(SUNGOLD_GOLD, 0.12)},
    "danger": {"accent": ALERT_RED, "bg": rgba(ALERT_RED, 0.08)},
}

# ---- Spacing -------------------------------------------------------------
SPACE_SM = "0.75rem"
SPACE_MD = "1.25rem"
SPACE_LG = "2rem"
