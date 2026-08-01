# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Streamlit (locked in Fase 0; see `docs/methodology.md`, "Dashboard tool: Streamlit" — not to be revisited). Python data pipeline (`src/`) already built and produces `data/processed/terroir.db`; the Streamlit dashboard itself has not been built yet. Streamlit dashboard deployed via Streamlit Community Cloud. Alongside it, a static HTML/CSS case study page, deployed via GitHub Pages (or alongside the existing Vercel setup), narrating the project and linking to the live dashboard.

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
  green `#0B4F3D`, lima green `#A8C93A`, SunGold gold `#F2A900`, alert
  red `#C0392B`, background `#E8E8E3`. Section breaks use a simple
  straight rule/line in an accent color, not diagonal cuts.

## Evidence on Hand

Real, already-computed results in `data/processed/terroir.db`: 22,834 LINZ parcels ingested across 4 territorial authorities, 21,491 scored, tables for `parcel_attributes`, `parcel_scores`, `subzone_summary`, `suitability_levels_summary`, `expansion_candidates`, `cross_project_comparison`, and `subzone_climate_risk`. Full reasoning and figures documented in `docs/methodology.md` and `docs/data_sources.md`. No testimonials, press, or case-study write-ups exist yet — do not fabricate any. No live deployment exists yet — both the Streamlit dashboard and the HTML case study are planned but not yet built or deployed.

## Product Principles

1. Truth over polish — never imply a finding is more certain or complete than the underlying data supports; documented caveats (synthetic-data comparison, unmatched-parcel gaps) stay visible, not smoothed away for a cleaner story.
2. Real data, real friction — the value proposition is genuine government-source data with genuine data-quality problems, surfaced and fixed, not hidden.
3. Credibility over spectacle — this is a technical-review (Operate/Read) surface, not a marketing (Persuade) surface; restraint and precision earn more trust than visual flourish.
4. Shared visual language with Apophenia only where it reinforces "same author, same rigor" — not decoration for its own sake.

## Accessibility & Inclusion

No specific standard mandated. General web accessibility good practice expected, given a professional technical audience.
