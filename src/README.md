# Source code

Reusable production code: data loading, the scoring model, and
geospatial utilities.

## Status

Twelve scripts so far, all following the Python header standard in
`docs/conventions.md`. Filenames used to carry a numeric prefix
(`00_explore_volumes.py`, `01_ingest_linz.py`, …) so pipeline order was
visible at a glance, but a name starting with a digit can't be
imported as a Python module — that blocked unit testing the scoring
logic, so the prefixes were dropped. **The list below is now the
canonical run order** — run top to bottom:

1. `explore_volumes.py` — exploratory, not the ingestion pipeline. No
  database writes. Confirms real data volume and geometry complexity for
  LINZ (122657), the four S-map layers, and LCDB (123148); validates the
  1 ha area threshold against the actual parcel distribution; and
  documents the LRIS WFS `bbox`/`CQL_FILTER` quirk (see
  `docs/data_sources.md`).
2. `ingest_linz.py` — production ingestion. Fetches LINZ Property
  Boundaries server-side filtered to the 4 target TAs + 1 ha area
  threshold, saves `data/processed/parcels_linz.geojson` (22,834
  parcels). Whakatane District was added as a 4th TA after
  `docs/data_sources.md`'s "Scope completeness verification" confirmed
  it holds real kiwifruit land the original 3-TA footprint excluded.
3. `ingest_soil_lcdb.py` — production ingestion. Computes a centroid
  per parcel, spatial-joins the four S-map layers and LCDB, and saves the
  result as `parcel_attributes` in `data/processed/terroir.db` (SQLite)
  — 94.1% S-map match rate, 99.7% LCDB match rate, see
  `docs/methodology.md` ("Handling unmatched parcels (nulls)").
4. `ingest_subzones.py` — production ingestion. Spatial-joins parcel
  centroids against LINZ layer 113764 (NZ Suburbs and Localities) to
  derive each parcel's Apophenia subzone (Tauranga, Katikati, Te Puke,
  Pongakawa, Opotiki), adding a `subzone` column to `parcel_attributes`
  — 18.0% of parcels fall within one of the 5 named subzones, by design
  (Whakatane District isn't one of them, so it's almost entirely NULL
  here) (see `docs/methodology.md`).
5. `ingest_parcel_groups.py` — production ingestion. Reads
  `parcels_linz.geojson` directly (not the database, since `source` is
  a geometry-level attribute) and flags each of the 22,834 raw
  features: `is_land_parcel = False` for the 2,866 road/hydro features
  that `ingest_linz.py`'s CQL_FILTER doesn't screen out; for the
  19,968 land rows, a `parcel_group_id` and `title_count` are assigned
  to every set of rows sharing an exact WKB geometry hash — safe as an
  exact match because `ingest_linz.py` already snaps every geometry to
  a 1e-6 degree precision grid. Adds `source_category`,
  `is_land_parcel`, `parcel_group_id`, and `title_count` columns to
  `parcel_attributes` via UPDATE — no rows added or removed. See
  `docs/methodology.md` ("Physical-parcel grouping: road/hydro
  exclusion and multi-title collapse").
6. `calculate_score.py` — scoring. Excludes the 2,866 road/hydro rows
  flagged by `ingest_parcel_groups.py`, then excludes land parcels
  with any null soil attribute (1,009 of 19,968), maps
  soil_order/soil_texture/soil_drainage/soil_depth to points and
  applies the weighted formula from `docs/methodology.md` ("Point
  tables", "Weights"), then collapses rows sharing a
  `parcel_group_id` into one row each (keeping `title_count`), saving
  the result as a new `parcel_scores` table (keyed on source_id) in
  `data/processed/terroir.db` — 16,072 distinct physical parcels
  scored.
7. `subzone_summary.py` — scoring. Joins `parcel_scores` with
  `parcel_attributes.subzone`, filters to the 5 named subzones (2,767
  parcels), and computes parcel count, mean score, and %
  Excellent/Good/Marginal per subzone, saved as `subzone_summary`. Bins
  with `right=False` so a score of exactly 5.0 or 8.0 lands in the
  higher tier, matching `docs/methodology.md`'s stated ranges exactly —
  see "Score distribution and suitability levels" for a boundary bug
  this fixed.
8. `cross_project_comparison.py` — scoring. Joins `subzone_summary`
  against Apophenia's `data/external/dim_corridor_apophenia.csv` on
  subzone name and correlates mean_score with Apophenia's 3 risk
  indicators, saved as `cross_project_comparison` — see
  `docs/methodology.md` ("Cross-project comparison (business question
  3)") for the real-vs-synthetic caveat this result is subject to.
9. `ingest_climate_risk.py` — production ingestion. Computes one
  representative point per subzone (average parcel centroid) and calls
  the Open-Meteo Historical Weather API (2016-2025) for each, saving
  frost days, chill hours, and heavy rain days (raw 10-year totals plus
  per-year figures) as `subzone_climate_risk` — see
  `docs/methodology.md` ("Climate risk ingestion (business question
  5)"). Unaffected by the Whakatane District scope expansion (not one of
  the 5 named subzones this script keys on), so it wasn't re-run when
  Whakatane was added.
10. `regional_summary_expansion.py` — scoring. Two parts: (1) groups
  all 16,072 scored parcels into suitability levels region-wide (not
  just the 5 named subzones) — Excellent 78.4%, Good 15.9%, Marginal
  5.7% — saved as `suitability_levels_summary`; (2) filters to
  suitability_score >= 8.0 AND not already LCDB-classified as orchard/
  vineyard/perennial crop, saved as `expansion_candidates` — 9,557
  parcels (75.8% of the Excellent tier). Same `right=False` boundary
  fix as `subzone_summary.py`. See `docs/methodology.md` ("Regional
  summary and expansion candidates (business questions 1 and 2)").
11. `export_parcel_scores_for_map.py` — export. Loads `parcel_scores`,
  reprojects each parcel's centroid from NZTM2000 to WGS84 for
  `lat`/`lon`, joins `territorial_authority` and `area_m2` from
  `parcels_linz.geojson`, adds `suitability_level` (same `right=False`
  bins as the scoring scripts above), and writes
  `data/powerbi_export/parcel_scores_for_map.csv` — one row per
  physical parcel, `title_count` included, saved as UTF-8 with a BOM
  (incidentally fixes prior "Ōpōtiki District" mojibake in the CSV).
12. `export_powerbi_summaries.py` — export. Regenerates the remaining
  Power BI-facing CSVs in `data/powerbi_export/` from the current
  `terroir.db` tables: `suitability_levels_summary.csv`,
  `subzone_summary.csv`, `expansion_candidates.csv`,
  `territorial_authority_summary.csv` (new), and a 500-row
  `parcel_scores_SAMPLE500.csv`. Does not touch
  `subzone_climate_risk.csv`, which is built independently of parcel
  grouping and is unaffected by this fix.

Plus two shared utilities, not part of the numbered pipeline order
above since they're imported by other scripts rather than run on
their own:

- `config.py` — the single source of truth for `PROJECT_ROOT`,
  `DB_PATH`, `PARCELS_PATH`, and `CORRIDOR_CSV_PATH`, plus
  `get_connection()`, a thin context-managed wrapper around
  `sqlite3.connect()`. Every other script and every dashboard page
  that touches `data/processed/` or `data/external/` imports these
  rather than redefining them locally — see CLAUDE.md, "Paths and
  configuration have one home".
- `api_retry.py` — `get_with_retry()`, a bounded exponential-backoff
  wrapper around `requests.get()` used by `ingest_linz.py` and
  `ingest_climate_risk.py`. Retries connection errors, timeouts, HTTP
  429, and HTTP 5xx; fails immediately on any other 4xx. See
  `docs/methodology.md`, "Retry policy for API ingestion".

All ingestion, joining, scoring, regional-summary/expansion,
cross-project comparison, and Power BI export work (Fase 2-4) is in
place. Fase 5 (Streamlit dashboard) is built — 6 pages, see
`dashboard/README.md`. Fase 6 (case study write-up) is built and live
too — see `case_study/README.md`.
