# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Streamlit (locked in Fase 0; see `docs/methodology.md`, "Dashboard tool: Streamlit" — not to be revisited). Python data pipeline (`src/`) built and produces `data/processed/terroir.db`; the Streamlit dashboard is built and deployed live via Streamlit Community Cloud at [terroir.streamlit.app](https://terroir.streamlit.app). Alongside it, a static HTML/CSS case study site — a separate repo/deploy, not generated from this repo's `case_study/` folder — is built and deployed via GitHub Pages at [gabrielaoliveranz.github.io/terroir-case-study](https://gabrielaoliveranz.github.io/terroir-case-study/), narrating the project and linking to the live dashboard; the dashboard's footer links to it in turn. `case_study/reference_design.html` in this repo is the visual design reference that preceded that site, kept for the record.

## Users

Hiring managers, recruiters, and technical interviewers evaluating Gabriela Olivera for data analyst / data engineer / GIS analyst roles — explicitly including council GIS/asset-management roles (e.g. Tauranga City Council, Western Bay of Plenty District Council, per `README.md`'s stated target audience). They are typically reviewing a portfolio under time pressure, scanning for technical credibility and clear communication rather than reading every line of code on a first pass.

## Product Purpose

A geospatial land-suitability case study for Bay of Plenty kiwifruit horticulture, demonstrating an end-to-end data analytics/engineering skillset: real government geospatial data ingestion (LINZ, S-map, LCDB, Open-Meteo), spatial joins, a documented scoring model, and cross-project analysis. Success means a reviewer leaves confident the candidate can independently execute a real, technically sound geospatial data project — not that they can style a dashboard around a toy dataset.

## Positioning

Distinct from typical portfolio dashboards by using real official NZ government geospatial sources rather than synthetic/Kaggle-style data, and by disclosing real data-quality issues found and fixed along the way (CRS mismatches, macron-spelling bugs, a non-unique join key, a scoring boundary bug — all in the public git history) rather than presenting a smoothed-over happy path. Sister project to Apophenia (`apophenia-nz.vercel.app`, kiwifruit export risk simulator) — together the two demonstrate range across operational-risk analysis and land-suitability analysis.

## Operating Context

Confirmed. The Streamlit dashboard will be deployed live via Streamlit
Community Cloud (free tier), connected to this GitHub repo — consistent
with Apophenia's live deployment on Vercel. The HTML case study is a
static page (GitHub Pages or alongside the Vercel setup), narrating the
project and linking to the live dashboard for interactive exploration.
Assume a short initial session (a few minutes) for most visitors, with a
smaller subset going deeper into the methodology/code or the live app.

## Capabilities and Constraints

- Dashboard presents already-computed results from `terroir.db` (parcel-level scores, subzone summaries, expansion candidates, climate risk, cross-project comparison) — not a live query/compute surface.
- The cross-project comparison against Apophenia uses **synthetic** corridor risk data on the Apophenia side (`data/external/dim_corridor_apophenia.csv`). Per `docs/methodology.md`, "Cross-project comparison (business question 3)", this caveat must stay visibly attached to that result wherever it's shown, not buried only in supporting docs.
- Data coverage gaps (e.g. ~5.9% of parcels have no S-map match) are disclosed, not hidden, per the project's existing null-handling policy.
- Writing conventions: en-NZ spelling throughout (established project convention).

## Brand Commitments

- Sister project to Apophenia (`apophenia-nz.vercel.app`).
- Tone: clean, technical, credible — explicitly not flashy or
  marketing-styled. No diagonal-cut banners, no stock photography, no
  script/handwritten fonts — those read as consumer marketing (Zespri's
  own site), which conflicts with this being a technical-review surface.
- Confirmed visual direction: bold, large typography as the primary
  visual device (not imagery), using the candidate palette — primary
  accent terracotta `#915117` (replacing the original primary green
  `#0B4F3D` as the general accent), lima green `#A8C93A`, SunGold gold
  `#F2A900`, alert red `#C0392B`, background `#E8E8E3`. Section breaks
  use a simple straight rule/line in an accent colour, not diagonal cuts.
- **Colour-role rule** (not just tribal knowledge — stated here so it's
  checked against, not re-derived from memory each time):
  - **Terracotta `#915117`** — general Terroir UI/interaction: buttons,
    CTA, dividers, section headers, links, hover states, the
    back-to-top button, the Analysis-column active/hover link state,
    the footer's Project icons (Apophenia, GitHub, LinkedIn alike — no
    per-icon colour distinction; an earlier version reserved primary
    green for Apophenia specifically, dropped per direct feedback in
    favour of one consistent accent across all three). This is "the
    app's own colour" — used wherever the interaction stays inside
    Terroir.
  - **Primary green `#0B4F3D`** — not used anywhere in the general
    dashboard UI. Stays confirmed in the brand palette itself (see
    above) and defined as a reference value in `dashboard/theme.py`,
    but nothing currently renders with it.
  - **SunGold gold `#F2A900`** — warning/callout only
    (`theme.CALLOUTS["warning"]`). Apophenia Comparison's
    synthetic-data disclaimer is the one place this renders; it stays
    gold, not terracotta — a warning shouldn't share a colour with a
    neutral action.
  - **Lima green `#A8C93A`** — confirmed brand colour, not currently
    assigned a UI role.
  - Explicitly excluded from all of the above: 2_Suitability_Map.py's
    and 3_Expansion_Candidates.py's blue/amber/deep-orange level
    colours, a separate accessibility-verified system (see that page's
    own docstring for the deuteranopia/protanopia simulation), not a
    brand-accent choice.
  Terracotta was proposed at `#B5651D` and checked the same way every
  other brand colour here is checked: it failed WCAG (white text on it
  measured 4.34:1, it measured 3.53:1 as text on the background — both
  need 4.5:1). Darkened to `#915117`, which clears both with margin
  (6.19:1 and 5.03:1 respectively) — see `dashboard/theme.py`'s
  `ACCENT` constant for the full derivation.

## Evidence on Hand

Real, already-computed results in `data/processed/terroir.db`: 22,834 LINZ parcels ingested across 4 territorial authorities, 16,072 distinct land parcels scored (road/hydro and duplicate legal-title records excluded — see `docs/methodology.md`), tables for `parcel_attributes`, `parcel_scores`, `subzone_summary`, `suitability_levels_summary`, `expansion_candidates`, `cross_project_comparison`, and `subzone_climate_risk`. Full reasoning and figures documented in `docs/methodology.md` and `docs/data_sources.md`. The Streamlit dashboard (6 pages) is built, verified working, and live at [terroir.streamlit.app](https://terroir.streamlit.app) — see `dashboard/README.md`. The narrated case study is built and deployed too, at [gabrielaoliveranz.github.io/terroir-case-study](https://gabrielaoliveranz.github.io/terroir-case-study/) (a separate repo/deploy from this one) — no testimonials or press exist beyond that, and none should be fabricated. See root `README.md`'s Roadmap for current status.

## Product Principles

1. Truth over polish — never imply a finding is more certain or complete than the underlying data supports; documented caveats (synthetic-data comparison, unmatched-parcel gaps) stay visible, not smoothed away for a cleaner story.
2. Real data, real friction — the value proposition is genuine government-source data with genuine data-quality problems, surfaced and fixed, not hidden.
3. Credibility over spectacle — this is a technical-review (Operate/Read) surface, not a marketing (Persuade) surface; restraint and precision earn more trust than visual flourish.
4. Shared visual language with Apophenia only where it reinforces "same author, same rigor" — not decoration for its own sake.

## Accessibility & Inclusion

No specific standard mandated. General web accessibility good practice expected, given a professional technical audience.
