# Dashboard

The Terroir analytical dashboard, built in Streamlit. See
`docs/methodology.md` for why Streamlit was chosen over Power BI.

## Structure

Multipage app using `st.Page` + `st.navigation` (the current recommended
pattern, Streamlit >= 1.36) — not the older auto-discovered `pages/`
directory convention, though page files still live under `pages/` with
numbered filenames for readability. Routing and order are controlled
explicitly in `streamlit_app.py`, not inferred from filenames.

```
dashboard/
├── streamlit_app.py            # entrypoint — defines pages, calls st.navigation
├── theme.py                     # design tokens ONLY — colours, spacing, shadow,
│                                 # callout variants. No Streamlit calls.
├── components.py                # rendering: accent_divider, footer, card_css,
│                                 # callout, metric_row, section_header, sr_only,
│                                 # label_chart, set_aria_label — all consume
│                                 # theme.py, none hardcode a value themselves
├── assets/icons/                # github.png, linkedin.png, kiwifruit.png —
│                                 # footer icons, see docs/attributions.md
├── pages/
│   ├── 0_Intro.py               # built — landing page
│   ├── 1_Overview.py            # built — KPI row + region-wide chart
│   ├── 2_Suitability_Map.py     # built — parcel-level pydeck map
│   ├── 3_Expansion_Candidates.py # built — pydeck map, LCDB-coloured
│   ├── 4_Apophenia_Comparison.py # built — cross-project comparison
│   └── 5_Climate_Risk.py        # built — frost/chill/rain by subzone
└── README.md
```

## Status

6 of 6 pages built:

- `0_Intro.py` — **built**. One-line description, link to Apophenia
  (sister project), the real differentiator (from `PRODUCT.md`'s
  Positioning section), and a link into Overview.
- `1_Overview.py` — **built**. KPI row (parcels ingested, parcels
  scored, % Excellent) from `suitability_levels_summary` /
  `parcel_scores` / `parcel_attributes`, plus a bar chart of the
  region-wide Excellent/Good/Marginal split.
- `2_Suitability_Map.py` — **built**. Parcel-level pydeck GeoJsonLayer
  map, geometry from `parcels_linz.geojson` joined with
  `suitability_score`/`subzone` from `parcel_scores`, coloured by level,
  with a subzone filter (5 named Apophenia subzones + "All") and a
  hover tooltip. Full precision genuinely exceeded Streamlit's 200MB
  message size limit for the "All" view (229MB) — geometry is
  simplified (~5m tolerance) and coordinates rounded (6dp) once at
  ingestion time in `src/ingest_linz.py`, not on every cold page
  load; see that script's and the page's own docstrings for the
  numbers.
- `3_Expansion_Candidates.py` — **built**. Parcel-level pydeck map of
  `expansion_candidates`, coloured/filterable by LCDB class instead of
  suitability level (subzone filter + LCDB class filter, both with
  "All"), hover tooltip, spinner on load. Excludes urban/settlement LCDB
  classes at the display layer (13,040 → 11,378 shown) — a known gap in
  the underlying `expansion_candidates` table itself, logged in
  `docs/methodology.md` as a refinement still to push back into
  `regional_summary_expansion.py`.
- `4_Apophenia_Comparison.py` — **built**. Business question 3:
  `cross_project_comparison` (5 subzones) shown as a real-vs-synthetic
  table (Terroir's `mean_score` next to Apophenia's 3 synthetic risk
  indicators), with correlations computed live from the loaded table
  (not hardcoded) and plain-language interpretation for each, including
  the near-zero one explicitly labelled "no meaningful relationship." A
  prominent `st.warning()` disclaimer sits at the top, and the -0.85
  PSA-incidence correlation carries its own caveat about Opotiki's
  outlier influence — recomputed without Opotiki (r = -0.76, n=4) to
  confirm the correlation survives removing it rather than assuming.
- `5_Climate_Risk.py` — **built**. Business question 5:
  `subzone_climate_risk` (5 subzones) shown as a table of the 3
  annualised metrics (frost days/year, chill hours/year avg, heavy rain
  days/year), with the raw 10-year totals for frost and heavy rain
  tucked into an expander (chill hours has no raw-total column, only
  the average). Interpretation covers near-zero frost region-wide, the
  coastal-vs-inland chill-hour split (grounded in the subzones' own
  lat/lon and known geography, not just the numbers), and Opotiki's
  standout heavy-rain frequency.

## Known issues

- **Overview (and other pages): direct URL navigation to a non-default
  page (e.g. loading `http://localhost:8501/Overview` fresh, rather than
  clicking through from the sidebar) triggers harmless 404 console
  errors** for `_stcore/health` and `_stcore/host-config` — Streamlit's
  frontend resolves those internal endpoints relative to the current
  path instead of root when the page is deep-linked directly. Confirmed
  this doesn't affect real usage (root load + sidebar navigation is
  always clean) — flagged for the final polish pass, not forgotten.
- **Suitability Map and Expansion Candidates: the pydeck basemap renders
  dark (CARTO's default dark-matter style), clashing with the rest of
  the app's light `#E8E8E3` theme.** Confirmed this affects both map
  pages, not just Suitability Map. pydeck/deck.gl's map style isn't
  controlled by `.streamlit/config.toml` — it needs its own explicit
  light-style `map_style` on each `pydeck.Deck` object. Flagged for the
  final polish pass — not forgotten.

## Design system

`theme.py` holds every derived visual value — colours, spacing, shadow,
callout variants — computed from the 5 confirmed brand colours via
explicit alpha-blend helpers, not eyeballed. `components.py` imports it
and does the actual rendering; nothing in `components.py` or any page
hardcodes a colour/shadow/spacing value on its own anymore. Both are
imported the same way from a page script (`sys.path.insert(...)` +
`from components import ...` / `import theme`, since Streamlit puts
each page script's own directory on `sys.path`, not `dashboard/` —
confirmed by testing a bare import first, which failed):

- **`theme.TEXT` (`#181410`)** — replaces Streamlit's unconfirmed
  default (`#31333F`). A comprehensive contrast audit (below) found
  `st.dataframe`'s canvas-rendered column headers failing WCAG at
  3.59:1 — CSS can't reach canvas content, so the only fix was
  darkening the global theme token. Header text renders at ~60%
  opacity of `textColor` (empirically derived, not documented by
  Streamlit); originally `#14151A` (a cool neutral-slate), moved to
  `#181410` (warm ink) in the reference-design pass — hue-matched to
  that design's ink family but luminance-matched to `#14151A`, not
  copied at face value, to keep clearing the header contrast fix
  (verified 4.79:1, not the reference's own literal ink value, which
  measured 4.46:1 and would have regressed it).
- **`theme.CHART_AXIS_COLOR` (`#5C564A`)** — Vega-Lite's default axis
  label grey measured 3.02:1 against the page background, a real
  failure. Applied via Altair's `axis=alt.Axis(labelColor=...,
  titleColor=...)`, computed to clear 4.5:1 with margin. Originally a
  cooler `#5A5C62` (5.44:1), moved to this warmer grey in the
  reference-design pass (5.92:1 — an improvement, not just a hue swap).
- **`callout(kind, message)`** — replaces `st.warning()`/`st.info()`.
  Streamlit's defaults (mustard yellow, light blue) aren't part of the
  confirmed palette and don't match anything else in the app; the
  warning box was also borderline-failing WCAG (4.48:1). Each variant
  (`info`/`warning`/`danger`) pairs a light tint of one confirmed accent
  colour with `theme.TEXT` — never the accent itself — as the message
  colour, verified at 13:1+.
- **`metric_row(metrics)`** — one elevated card per KPI via
  `st.columns`, not one shared container. Used by Overview (3 metrics)
  and Expansion Candidates (1, for consistency).
- **`card_css(*keys, padding=...)`** — surface styling (solid white
  background, a neutral-ink border, generous padding). Went through
  several rounds: a near-invisible border+tint, a bumped-opacity
  border+tint that still read as flat, a soft two-layer shadow that
  stuck for a while, and — in the reference-design pass — sharp 2px
  corners with the shadow dropped entirely (that design uses zero
  box-shadow anywhere; depth comes from background/border contrast,
  not elevation) and the border switched from accent-tinted to neutral
  ink, reserving the accent colour for interactive/emphasis elements
  only. `hoverable=True` used to lift the card with a stronger shadow;
  with no shadow left to deepen, it now darkens the border toward
  `theme.ACCENT` instead (`CARD_BORDER_HOVER`).
- **`accent_divider()`** — the straight-line accent-coloured rule from
  `0_Intro.py`'s original polish pass, now the one section-break
  treatment on every page (one per page, at its clearest content-type
  boundary — restrained on purpose).
- **`section_header(text)`** — replaces bare `st.subheader()` with the
  same size/weight (28px/600, matched via computed style) plus a short
  accent-coloured mark to the left.
- **`footer()`** — three columns (Analysis: `st.page_link` to all 6
  pages; Data Sources: real LINZ/S-map/LCDB/Open-Meteo URLs; Project:
  Apophenia/GitHub/LinkedIn with icons), a live case-study CTA, and
  a copyright line — carried by spacing, a subtle divider, and
  typography, **not** a coloured background. A full-bleed solid-green
  version shipped previously; removed after feedback that it read as
  visually disconnected from the sidebar, plus it needed overriding
  four separate Streamlit flex-layout constraints (flex-shrink,
  flex-basis, `align-items:stretch` on a `flex-direction:column`
  parent, and `stVerticalBlock`'s own `max-width:100%`) just to bleed
  edge-to-edge — a lot of fragile surface area for a look that turned
  out not to be wanted. Icons are now the natural black (no CSS
  recolour filter needed, since there's no coloured background to
  recolour them against).
- **`LEVEL_PALETTE_HEX` / `LEVEL_PALETTE_HOVER_HEX`** — hex-string
  mirror of `2_Suitability_Map.py`'s colourblind-safe `LEVEL_COLORS`,
  for Altair charts that want CSS colours instead of RGBA arrays. Used
  by Overview's bar chart for one consistent colour language.
- **Overview's bar chart hover**: `st.altair_chart`, two stacked layers
  (static base + opacity-conditional highlight in a computed lighter
  shade) — `alt.condition()` with a field-based `Color` on both
  branches hits a real bug in Altair 6.2.2, isolated in a standalone
  repro before working around it. Bumped from a 40% to 60% white-blend
  after feedback that the shift wasn't visible enough; re-verified with
  an actual before/after screenshot (not just computed style — an
  earlier "verified" claim based on computed style alone turned out to
  need this).
- **Sidebar/footer link hover**: Streamlit ships a sidebar hover
  already (confirmed via computed style, `rgba(163,163,143,0.15)`) but
  it's barely perceptible and off-brand grey — reinforced with
  `theme.HOVER_TINT` everywhere a hover state exists in the app.
- **Accessibility helpers** — `sr_only()`, `label_chart()` /
  `set_aria_label()` (pydeck map descriptions and labels — see the
  functions' own docstrings for the iframe-assumption bug this
  corrected). Focus indicators checked via computed style (~10:1
  contrast, no reinforcement needed) and keyboard navigation verified
  via Playwright, both unchanged from the previous pass.
- **Table styling**: explicit `column_config` right-aligns numeric
  columns, left-aligns Subzone, consistent decimal formatting.
- **Copy pass (corpo tone)**: every visitor-facing description and
  disclaimer rewritten in plain business language — no "n=5", no
  "provenance", no internal file paths or script names leaking into
  captions. Every factual claim is unchanged.
- **Reference-design pass** (tokens extracted from a Claude-built case
  study mockup, `case_study/reference_design.html` — see that file's
  own status note, this is a visual reference, not the live case
  study): `theme.HEADING_FONT` ('Archivo', loaded as `[theme]
  headingFont` in `.streamlit/config.toml` via Google Fonts — verified
  actually loading, not just configured, via `document.fonts`), sharp
  `CARD_RADIUS`/`BUTTON_RADIUS` (2px, was 12px), zero shadows anywhere,
  `theme.BUTTON_OUTLINE_*` (a transparent/ink-border secondary button
  variant, used live on the footer's case-study CTA), and
  `theme.KICKER_*` (the uppercase eyebrow-label treatment, used on the
  footer's 3 column headings). Not matched from the reference: fluid
  clamp()-scaled hero typography and full-bleed section backgrounds —
  neither is achievable inside Streamlit's fixed-width, persistent-
  sidebar layout without fragile CSS hacking, so neither was faked.

### Contrast audit

A full scan of every rendered text-colour/background pair across all 6
pages, including Streamlit's own defaults (captions, table headers,
chart axis labels, sidebar nav) — not just the 4 brand colours. 19
unique pairs measured; 2 real failures found and fixed (dataframe
headers, chart axis labels — both above); 2 more initially looked like
failures but were a bug in the scan script itself (it didn't composite
a translucent callout background over its ancestor before computing
luminance — corrected by hand, confirmed 13:1+). Full table with every
pair, colour values, and ratios is in the design polish report, not
just this summary.

## Design notes

- **Expansion Candidates: ~52% of subzone x LCDB-class filter
  combinations return zero results (69 of 132 possible pairs) — this is
  expected, not a data gap.** Smaller subzones only have a handful of
  the 22 LCDB classes present at all (Opotiki 3, Katikati 4, Pongakawa
  6), so most combinations are legitimately empty. The page shows a
  clear "No candidates match..." message for these rather than an empty
  or broken map — see the page's own docstring for how this was
  confirmed (and the crash it used to cause before the empty-state
  check was added).

## Running locally

```
streamlit run dashboard/streamlit_app.py
```
