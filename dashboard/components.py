# =============================================================================
# TERROIR — Shared dashboard components
# Script: components.py
# Stage:  Dashboard (Fase 5)
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Rendering functions for the shared UI pieces used across all 6 pages —
cards, dividers, callouts, KPI metrics, the footer, accessibility
helpers. Every colour/spacing/shadow value here comes from theme.py,
not a hardcoded literal — this file is "how things render", theme.py
is "what the values are". That split means a palette or spacing change
happens in exactly one place (theme.py) instead of being hunted down
across every function here.

Import from a page script with:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from components import accent_divider, footer

The sys.path insert is necessary because Streamlit puts each page
script's own directory (pages/) on sys.path when running it, not the
dashboard/ directory this module lives in — confirmed by testing a
bare `import components` first, which raised ModuleNotFoundError.
"""

import base64
import re
from pathlib import Path

import streamlit as st

import theme

ICONS_DIR = Path(__file__).resolve().parent / "assets" / "icons"

# Footer content — single source of truth for the "Analysis" (internal
# page), "Data Sources" (external, real URLs — see docs/attributions.md
# and docs/data_sources.md for provenance of each), and "Project" (icon
# + external link) columns.
FOOTER_PAGES = [
    ("Intro", "pages/0_Intro.py"),
    ("Overview", "pages/1_Overview.py"),
    ("Suitability Map", "pages/2_Suitability_Map.py"),
    ("Expansion Candidates", "pages/3_Expansion_Candidates.py"),
    ("Apophenia Comparison", "pages/4_Apophenia_Comparison.py"),
    ("Climate Risk", "pages/5_Climate_Risk.py"),
]

DATA_SOURCES = [
    ("LINZ", "https://data.linz.govt.nz/layer/122657-nz-property-boundaries/"),
    ("S-map", "https://lris.scinfo.org.nz"),
    ("LCDB", "https://lris.scinfo.org.nz/layer/123148/"),
    ("Open-Meteo", "https://open-meteo.com/en/docs/historical-weather-api"),
]

# Apophenia uses the kiwifruit mark; GitHub/LinkedIn use their own logo
# marks — see docs/attributions.md for sourcing. All three are
# monochrome black PNGs on transparent backgrounds, rendered at their
# natural colour now that the footer has no coloured background to
# recolor them against (see footer()'s own docstring for why that
# background was removed).
PROJECT_LINKS = [
    ("Apophenia", "https://apophenia-nz.vercel.app", "kiwifruit.png"),
    ("GitHub", "https://github.com/gabrielaoliveranz", "github.png"),
    ("LinkedIn", "https://www.linkedin.com/in/gabriela-olivera-nz/", "linkedin.png"),
]


def _icon_data_uri(filename):
    data = base64.b64encode((ICONS_DIR / filename).read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def _icon_img(filename):
    """Inline <img> for a local icon file, sized to 1em so it tracks the
    surrounding text's font-size."""
    return (
        f'<img src="{_icon_data_uri(filename)}" alt="" '
        f'style="width:1em; height:1em; vertical-align:-0.15em; display:inline-block;">'
    )


def _icon_badge(filename):
    """Icon wrapped in a fixed-size circle (.footer-icon) for the
    hover-backdrop effect: on :hover, footer()'s style block fills the
    circle with theme.ACCENT — matching the Towards Data Science
    reference style of a solid accent-colour circle appearing behind an
    otherwise-plain icon on hover. All three Project icons (Apophenia,
    GitHub, LinkedIn) get identical treatment, no per-icon colour
    distinction — an earlier version reserved PRIMARY_GREEN for
    Apophenia specifically (signalling "leaves this project"), dropped
    per direct feedback in favour of one consistent accent everywhere.

    The glyph itself is a masked <span>, not a bare <img>: these source
    PNGs are plain black-on-transparent silhouettes (confirmed via pixel
    inspection — every opaque pixel in all three is (0,0,0)), so
    `mask-image` using the PNG as an alpha mask lets the glyph's own
    `background-color` paint through it — an exact colour, not an
    approximation via CSS filter chains (the previous version used
    `filter:brightness(0) invert(1)` on hover only, which only ever
    produced black-or-white; recolouring the *rest* state to a specific
    accent hex isn't something that trick can do). Rest state is
    theme.ACCENT for all three icons (GitHub/LinkedIn/Apophenia alike);
    hover swaps the glyph to white, readable against whichever accent
    colour fills the circle behind it.
    """
    return (
        f'<span class="footer-icon">'
        f'<span class="footer-icon-glyph" style='
        f'"mask-image:url({_icon_data_uri(filename)});'
        f'-webkit-mask-image:url({_icon_data_uri(filename)});" ></span>'
        f"</span>"
    )


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def accent_divider():
    """Subtle straight-line rule in the accent colour, replacing st.divider().

    Originally built for 0_Intro.py's polish pass; extracted here so
    every page and the footer reuse the same divider token
    (theme.DIVIDER_COLOR/DIVIDER_OPACITY) instead of each inventing its
    own section-break treatment.
    """
    st.html(
        f'<hr style="border:none; border-top:1px solid {theme.DIVIDER_COLOR}; '
        f'opacity:{theme.DIVIDER_OPACITY}; margin:1.75rem 0;">'
    )


def card_css(*keys, padding="1.5rem 1.75rem", hoverable=False):
    """Elevated-surface card styling (theme.CARD_BG/BORDER/SHADOW) for
    one or more `key=` values passed to st.container(...) or
    st.expander(..., key=...).

    `padding` defaults to a generous inset for st.container groups
    (e.g. a KPI card); pass padding="0.25rem" for st.expander, which
    already manages its own internal header/body spacing — the full
    default would double up the gap (checked visually, not assumed).

    `hoverable=True` adds a subtle lift on :hover (a slightly stronger
    two-layer shadow, theme.CARD_SHADOW_HOVER, plus a small upward
    translate) — used for KPI cards specifically, which are meant to
    read as small independent tiles; not the default, since it would be
    an odd affordance on non-interactive surfaces like the expander
    cards or the Climate Risk insights card (hovering them doesn't do
    anything, so a lift there would suggest an interaction that isn't
    there).
    """
    selectors = ", ".join(f".st-key-{k}" for k in keys)
    hover_css = ""
    if hoverable:
        hover_css = (
            f"{selectors} {{ transition: box-shadow 0.18s ease, transform 0.18s ease; }}"
            f"{selectors}:hover {{ box-shadow:{theme.CARD_SHADOW_HOVER}; "
            f"transform: translateY(-3px); }}"
        )
    st.html(
        f"<style>{selectors} {{ background:{theme.CARD_BG}; border:{theme.CARD_BORDER}; "
        f"border-radius:{theme.CARD_RADIUS}; box-shadow:{theme.CARD_SHADOW}; "
        f"padding:{padding}; }} {hover_css}</style>"
    )


# Mirrors 2_Suitability_Map.py's LEVEL_COLORS (colorblind-safe blue ->
# amber -> deep-orange scheme, verified there via colorspacious). Kept
# as a second, hex-string copy rather than importing pydeck-format RGBA
# lists across pages — this is for non-pydeck charts (Altair/Vega-Lite),
# which want hex/CSS colours, not RGBA arrays. If the map's palette ever
# changes, update both — small enough surface area that a shared
# converter would be more indirection than it's worth.
LEVEL_PALETTE_HEX = {"Excellent": "#003F91", "Good": "#FFB02E", "Marginal": "#C43900"}
# 60%-white-blended lighter shades, computed (not eyeballed) for the
# bar chart's hover state — see 1_Overview.py for where this is used.
LEVEL_PALETTE_HOVER_HEX = {"Excellent": "#99B2D3", "Good": "#FFDFAB", "Marginal": "#E7B099"}


def section_header(text):
    """Section heading with a small accent-coloured mark to its left,
    replacing bare st.subheader() for stronger visual hierarchy.
    Matches st.subheader's own size/weight (28px/600 — checked via
    computed style before choosing these values, not guessed) so it
    reads as an amplification of Streamlit's own hierarchy, not an
    unrelated new style bolted on. Text colour is explicit theme.TEXT
    now (matches the global textColor theme setting) rather than a
    separate hardcoded value.
    """
    st.html(
        f'<div style="display:flex; align-items:center; gap:0.65rem; '
        f'margin:2rem 0 0.9rem;">'
        f'<div style="width:5px; height:1.5rem; background:{theme.ACCENT}; '
        f'border-radius:2px; flex-shrink:0;"></div>'
        f'<span style="font-size:28px; font-weight:600; letter-spacing:-0.015em; '
        f'color:{theme.TEXT};">{text}</span></div>'
    )


def style_metrics(key):
    """Gives an st.container(key=...) full of st.metric widgets more
    typographic presence: the big value in the accent colour and the
    small label uppercased with letter-spacing (the standard dashboard
    "eyebrow label" convention). Call alongside card_css(key).
    """
    st.html(
        f"""<style>
        .st-key-{key} [data-testid="stMetricValue"] {{ color: {theme.ACCENT}; }}
        .st-key-{key} [data-testid="stMetricLabel"] {{
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-size: 0.75rem;
        }}
        </style>"""
    )


def metric_row(metrics):
    """Renders each (label, value) pair in its own elevated card, laid
    out side by side — not one shared card wrapping every metric (the
    earlier version): each KPI is visually a separate, independent
    number, which is what st.columns + a card per column gives you
    that a single st.container(horizontal=True) card doesn't.
    """
    cols = st.columns(len(metrics), gap="medium")
    for col, (label, value) in zip(cols, metrics):
        key = f"kpi-card-{_slug(label)}"
        with col:
            with st.container(key=key):
                st.metric(label, value)
            card_css(key, hoverable=True)
            style_metrics(key)


def callout(kind, message):
    """Token-styled callout, replacing st.warning()/st.info() — those
    render in Streamlit's own default colours (a mustard yellow for
    warning that isn't part of the confirmed palette and doesn't match
    anything else in the app, confirmed via a contrast audit to be
    borderline-failing WCAG besides: 4.48:1 against the 4.5:1 minimum).

    `kind` is one of theme.CALLOUTS's keys ("info", "warning",
    "danger") — each pairs a light tint of one confirmed accent colour
    with TEXT (never the accent itself) as the message colour, verified
    to pass contrast with wide margin (13:1+) rather than assumed safe.
    `message` accepts the same markdown (bold, links) st.markdown does.
    """
    variant = theme.CALLOUTS[kind]
    st.html(
        f'<div style="background:{variant["bg"]}; border-left:3px solid {variant["accent"]}; '
        f'border-radius:6px; padding:1rem 1.25rem; margin:0.5rem 0; '
        f'color:{theme.TEXT};">{_markdown_to_html(message)}</div>'
    )


def _markdown_to_html(text):
    """Minimal **bold** support — callout() takes short messages, not
    full markdown documents, so a tiny regex is proportionate rather
    than pulling in a markdown renderer for one tag."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def sr_only(text):
    """Visually-hidden but screen-reader-readable text.

    Used ahead of pydeck maps: even labelled correctly (see label_chart()
    below), a WebGL <canvas> has no per-parcel semantic content a screen
    reader can enumerate — the colour-coding itself is inherently visual.
    This is the standard fix: describe what the visualisation shows in
    text a sighted user never sees but a screen reader always announces,
    read in-line as part of the page instead of only as an element label.
    """
    st.html(
        f'<span style="position:absolute; width:1px; height:1px; padding:0; '
        f'margin:-1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; '
        f'border:0;">{text}</span>'
    )


def set_aria_label(selector, description, role="img"):
    """Sets role/aria-label on the first element matching `selector`.

    Polls briefly (Streamlit component elements can mount a beat after
    the rest of the page settles) and degrades silently if the element
    never appears. `unsafe_allow_javascript=True` is safe here — the
    script body is a fixed, developer-authored string, never user input.
    """
    st.html(
        f"""<script>
        (function() {{
            let tries = 0;
            const interval = setInterval(function() {{
                const el = document.querySelector({selector!r});
                if (el) {{
                    el.setAttribute('role', {role!r});
                    el.setAttribute('aria-label', {description!r});
                    clearInterval(interval);
                }}
                if (++tries > 40) clearInterval(interval);
            }}, 250);
        }})();
        </script>""",
        unsafe_allow_javascript=True,
    )


def label_chart(description):
    """Sets role="img" + aria-label directly on the pydeck chart's own
    wrapper element ([data-testid="stDeckGlJsonChart"] — confirmed via
    DOM inspection to render in-page, not inside an iframe). Safe
    unqualified since each page that calls this has exactly one pydeck
    chart. The sr_only() text above the chart is what actually
    guarantees the content reaches a screen reader either way — this is
    a second, lower-effort channel (an object-navigation label), not
    the primary fix.
    """
    set_aria_label('[data-testid="stDeckGlJsonChart"]', description)


def back_to_top():
    """Floating circular "back to top" button, fixed bottom-right,
    hidden until the page has scrolled down and smooth-scrolling back
    to the top on click.

    Streamlit's real scrollable element is [data-testid="stMain"] (its
    computed overflow is auto; window/body and stAppViewContainer are
    overflow:hidden, stMainBlockContainer is overflow:visible — checked
    directly via computed style and scrollHeight/clientHeight before
    writing this, not assumed) — the scroll listener and scrollTo both
    target that element, not window.

    The arrow is a CSS-drawn chevron (two rotated border edges), not an
    <svg>/<path> — st.html()'s sanitizer strips both tags entirely
    (confirmed via DOM inspection: the button rendered as a bare empty
    circle, no console error, nothing flagging why — outerHTML showed
    the <svg> just wasn't there). CSS avoids the sanitizer question
    altogether rather than working around it.
    """
    st.html(
        f"""
        <style>
        #terroir-back-to-top {{
            position: fixed;
            right: 1.75rem;
            bottom: 1.75rem;
            width: 3rem;
            height: 3rem;
            border-radius: 50%;
            background: {theme.BUTTON_BG};
            box-shadow: {theme.BUTTON_SHADOW};
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            opacity: 0;
            transform: translateY(12px);
            pointer-events: none;
            transition: opacity 0.2s ease, transform 0.2s ease, background-color 0.15s ease;
            z-index: 999;
        }}
        #terroir-back-to-top.visible {{
            opacity: 1;
            transform: translateY(0);
            pointer-events: auto;
        }}
        #terroir-back-to-top:hover {{
            background: {theme.BUTTON_BG_HOVER};
        }}
        #terroir-back-to-top .chevron {{
            width: 0.7rem;
            height: 0.7rem;
            border-top: 2.5px solid {theme.BUTTON_TEXT};
            border-right: 2.5px solid {theme.BUTTON_TEXT};
            transform: rotate(-45deg) translate(-1px, 1px);
        }}
        </style>
        <div id="terroir-back-to-top" role="button" aria-label="Back to top" tabindex="0">
            <span class="chevron"></span>
        </div>
        <script>
        (function() {{
            function init() {{
                const main = document.querySelector('[data-testid="stMain"]');
                const btn = document.getElementById('terroir-back-to-top');
                if (!main || !btn) return false;
                main.addEventListener('scroll', function() {{
                    if (main.scrollTop > 400) {{
                        btn.classList.add('visible');
                    }} else {{
                        btn.classList.remove('visible');
                    }}
                }});
                const scrollToTop = function() {{ main.scrollTo({{ top: 0, behavior: 'smooth' }}); }};
                btn.addEventListener('click', scrollToTop);
                btn.addEventListener('keydown', function(e) {{
                    if (e.key === 'Enter' || e.key === ' ') {{ e.preventDefault(); scrollToTop(); }}
                }});
                return true;
            }}
            if (!init()) {{
                let tries = 0;
                const interval = setInterval(function() {{
                    if (init() || ++tries > 40) clearInterval(interval);
                }}, 250);
            }}
        }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def footer():
    """Site footer: three columns (Analysis: links to all 6 pages;
    Data Sources: real external URLs, see DATA_SOURCES; Project:
    Apophenia/GitHub/LinkedIn with icons), a disabled case-study CTA,
    and a copyright line — carried by spacing, a subtle top divider,
    and typography, not a coloured background block.

    A full-bleed solid-green version of this shipped previously. Two
    problems with it, both from direct feedback: it read as visually
    disconnected/"floating" relative to the sidebar (a coloured band
    starting exactly at the sidebar's edge draws a hard seam a plain
    divider doesn't), and getting it to actually bleed edge-to-edge
    took overriding four separate Streamlit flex-layout constraints —
    a lot of fragile surface area for a look that wasn't wanted anyway.
    Removing the background removes that whole problem along with it:
    no full-bleed script, no flex overrides, just accent_divider() plus
    normal in-flow layout.

    Also renders back_to_top() — every page calls footer() exactly once
    at the bottom, so it's the one place global-chrome elements (this,
    the sidebar-nav-hover rule, the selectbox styling above) can live
    without being duplicated per page.

    Analysis-column links behave exactly like Data Sources' now: plain
    text, no background ever, theme.ACCENT text colour on hover only,
    no bold — no separate "active page" treatment. An earlier version
    gave the current page a solid filled pill (reinforcing Streamlit's
    own native active-page marker, a grey rgba(163,163,143,0.15)
    background plus bold text) with hover as a lighter/text-only
    variant; dropped per direct feedback in favour of one plain,
    uniform link style with no active/hover distinction to confuse.
    Streamlit's native marker still has to be explicitly overridden
    (background:transparent, font-weight:400) rather than just left
    alone, since it applies unconditionally to whichever link matches
    the current page regardless of what this app's own CSS does.

    CSS comments inside the final st.html() string below are kept short
    on purpose — they're payload, not documentation, sent to the browser
    on every page load. A verbose comment pass here once pushed that one
    st.html() call's content past whatever size Streamlit needs to
    reliably deliver it; it started rendering nothing at all (no
    exception, just absent from the DOM), and the failure was silent
    enough that it looked identical to a real CSS/specificity bug until
    the payload was actually measured. Put the reasoning in Python
    comments and docstrings like this one instead, and keep the CSS
    itself lean.
    """
    back_to_top()
    accent_divider()

    with st.container(key="site-footer"):
        cols = st.columns(3, gap="large")

        with cols[0]:
            st.html('<p class="footer-heading">Analysis</p>')
            for label, path in FOOTER_PAGES:
                st.page_link(path, label=label)

        with cols[1]:
            st.html('<p class="footer-heading">Data Sources</p>')
            # footer-source-link exists so the hover rule below can target
            # just this column — Project's plain <a> tags share the same
            # .footer-line wrapper but already get their own distinguishing
            # treatment (the icon-circle hover), so they're deliberately
            # left out of this rule rather than doubling up two hover cues
            # on the same link.
            sources_html = "".join(
                f'<div class="footer-line"><a class="footer-source-link" href="{url}" '
                f'target="_blank" rel="noopener noreferrer">{label}</a></div>'
                for label, url in DATA_SOURCES
            )
            st.html(sources_html)

        with cols[2]:
            st.html('<p class="footer-heading">Project</p>')
            # All three icons get identical hover treatment — see
            # _icon_badge()'s docstring for the earlier per-icon colour
            # distinction this replaced.
            project_html = "".join(
                f'<div class="footer-line">{_icon_badge(icon)} '
                f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a></div>'
                for label, url, icon in PROJECT_LINKS
            )
            st.html(project_html)

        st.html(
            '<div class="footer-cta" aria-disabled="true">'
            "Read the full case study &rarr; "
            '<span class="footer-cta-soon">(coming soon)</span>'
            "</div>"
        )
        st.html('<div class="footer-copyright">&copy; 2026 Gabriela Olivera &middot; Terroir</div>')

    # Split into two st.html() calls, not one — a single call this size
    # (~4.8KB source) was found to silently render as nothing at all (no
    # exception, absent from the DOM) on a meaningful fraction of loads.
    # A prior round "fixed" an earlier instance of this by shrinking the
    # content, which held until this round's edits made it smaller still
    # and it broke again — so it isn't a clean fixed-size threshold,
    # more likely some per-call delivery limit/race that two smaller
    # calls sidestep rather than something worth continuing to chase.
    st.html(
        f"""
        <style>
        .st-key-site-footer {{ margin-top: 0.5rem; color: {theme.TEXT}; }}
        .st-key-site-footer .footer-heading {{
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.75rem;
            color: {theme.TEXT_MUTED};
            margin: 0 0 0.9rem;
            font-weight: 600;
        }}
        .st-key-site-footer .footer-line {{ margin-bottom: 0.55rem; display: flex; align-items: center; gap: 0.5rem; }}
        .st-key-site-footer .footer-icon {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 1.75rem;
            height: 1.75rem;
            border-radius: 50%;
            flex-shrink: 0;
            transition: background-color 0.15s ease;
        }}
        .st-key-site-footer .footer-icon-glyph {{
            width: 1em;
            height: 1em;
            display: block;
            background-color: {theme.ACCENT};
            mask-size: contain;
            mask-repeat: no-repeat;
            mask-position: center;
            -webkit-mask-size: contain;
            -webkit-mask-repeat: no-repeat;
            -webkit-mask-position: center;
            transition: background-color 0.15s ease;
        }}
        .st-key-site-footer .footer-line:hover .footer-icon {{
            background-color: {theme.ACCENT};
        }}
        .st-key-site-footer .footer-line:hover .footer-icon-glyph {{
            background-color: #FFFFFF;
        }}
        .st-key-site-footer a,
        .st-key-site-footer [data-testid="stPageLink"] p {{
            color: {theme.TEXT} !important;
            opacity: 0.75;
            text-decoration: none;
            font-size: 0.9rem;
            transition: opacity 0.15s ease, text-decoration-color 0.15s ease;
        }}
        .st-key-site-footer a:hover,
        .st-key-site-footer [data-testid="stPageLink"]:hover p {{
            opacity: 1;
            text-decoration: underline;
        }}
        .st-key-site-footer a.footer-source-link:hover {{
            color: {theme.ACCENT} !important;
        }}
        .footer-cta {{
            display: inline-block;
            margin-top: 2.25rem;
            padding: 0.6rem 1.1rem;
            border: 1px solid {theme.rgba(theme.ACCENT, 0.25)};
            border-radius: 6px;
            color: {theme.TEXT_MUTED};
            font-weight: 600;
            font-size: 0.9rem;
            cursor: not-allowed;
            user-select: none;
        }}
        .footer-cta-soon {{ font-weight: 400; opacity: 0.8; }}
        .footer-copyright {{
            margin-top: 1.75rem;
            padding-top: 1.5rem;
            border-top: 1px solid {theme.rgba(theme.ACCENT, 0.15)};
            font-size: 0.8rem;
            color: {theme.TEXT_MUTED};
        }}
        </style>
        """
    )

    # No active/hover distinction on Analysis links — plain text always,
    # matching Data Sources exactly. background/padding overrides here
    # fight Streamlit's own native styling (a persistent grey "current
    # page" marker background, plus 8px left padding it ships on every
    # page_link anchor regardless) — both apply unconditionally unless
    # explicitly squashed, not just for the current page. The padding
    # one is easy to miss: it doesn't misrender on its own, it just
    # leaves the text indented 8px versus Data Sources' plain <a> (never
    # padded), so the two columns' headings and links stop lining up.
    st.html(
        f"""
        <style>
        .st-key-site-footer [data-testid="stPageLink"] {{ min-height: 0; padding: 0.15rem 0; }}
        .st-key-site-footer [data-testid="stPageLink"] a {{
            background-color: transparent !important;
            padding: 0 !important;
        }}
        .st-key-site-footer [data-testid="stPageLink"] p {{
            font-weight: 400 !important;
        }}
        .st-key-site-footer [data-testid="stPageLink"] a:hover p {{
            color: {theme.ACCENT} !important;
        }}
        [data-testid="stSidebarNav"] a:hover {{
            background-color: {theme.HOVER_TINT} !important;
        }}
        [data-testid="stSelectbox"] [role="group"] {{
            background-color: {theme.INPUT_BG} !important;
            border-color: {theme.INPUT_BORDER} !important;
            transition: border-color 0.15s ease, box-shadow 0.15s ease;
        }}
        [data-testid="stSelectbox"] [role="group"]:hover {{
            border-color: {theme.INPUT_BORDER_HOVER} !important;
        }}
        [data-testid="stSelectbox"] [role="group"]:focus-within {{
            border-color: {theme.INPUT_BORDER_HOVER} !important;
            box-shadow: {theme.INPUT_FOCUS_RING};
        }}
        </style>
        """
    )
