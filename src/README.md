# Source code

Reusable production code: data loading, the scoring model, and
geospatial utilities.

## Status

Nine scripts so far, all following the Python header standard in
`docs/conventions.md`:

- `00_explore_volumes.py` — exploratory, not the ingestion pipeline. No
  database writes. Confirms real data volume and geometry complexity for
  LINZ (122657), the four S-map layers, and LCDB (123148); validates the
  1 ha area threshold against the actual parcel distribution; and
  documents the LRIS WFS `bbox`/`CQL_FILTER` quirk (see
  `docs/data_sources.md`).
- `01_ingest_linz.py` — production ingestion. Fetches LINZ Property
  Boundaries server-side filtered to the 4 target TAs + 1 ha area
  threshold, saves `data/processed/parcels_linz.geojson` (22,834
  parcels). Whakatane District was added as a 4th TA after
  `docs/data_sources.md`'s "Scope completeness verification" confirmed
  it holds real kiwifruit land the original 3-TA footprint excluded.
- `02_ingest_soil_lcdb.py` — production ingestion. Computes a centroid
  per parcel, spatial-joins the four S-map layers and LCDB, and saves the
  result as `parcel_attributes` in `data/processed/terroir.db` (SQLite)
  — 94.1% S-map match rate, 99.7% LCDB match rate, see
  `docs/methodology.md` ("Handling unmatched parcels (nulls)").
- `03_ingest_subzones.py` — production ingestion. Spatial-joins parcel
  centroids against LINZ layer 113764 (NZ Suburbs and Localities) to
  derive each parcel's Apophenia subzone (Tauranga, Katikati, Te Puke,
  Pongakawa, Opotiki), adding a `subzone` column to `parcel_attributes`
  — 18.0% of parcels fall within one of the 5 named subzones, by design
  (Whakatane District isn't one of them, so it's almost entirely NULL
  here) (see `docs/methodology.md`).
- `04_calculate_score.py` — scoring. Excludes parcels with any null soil
  attribute (1,343 of 22,834), maps soil_order/soil_texture/soil_drainage/
  soil_depth to points and applies the weighted formula from
  `docs/methodology.md` ("Point tables", "Weights"), saving the result as
  a new `parcel_scores` table (keyed on source_id) in
  `data/processed/terroir.db` — 21,491 parcels scored.
- `05_subzone_summary.py` — scoring. Joins `parcel_scores` with
  `parcel_attributes.subzone`, filters to the 5 named subzones (4,104
  parcels), and computes parcel count, mean score, and %
  Excellent/Good/Marginal per subzone, saved as `subzone_summary`. Bins
  with `right=False` so a score of exactly 5.0 or 8.0 lands in the
  higher tier, matching `docs/methodology.md`'s stated ranges exactly —
  see "Score distribution and suitability levels" for a boundary bug
  this fixed.
- `06_cross_project_comparison.py` — scoring. Joins `subzone_summary`
  against Apophenia's `data/external/dim_corridor_apophenia.csv` on
  subzone name and correlates mean_score with Apophenia's 3 risk
  indicators, saved as `cross_project_comparison` — see
  `docs/methodology.md` ("Cross-project comparison (business question
  3)") for the real-vs-synthetic caveat this result is subject to.
- `07_ingest_climate_risk.py` — production ingestion. Computes one
  representative point per subzone (average parcel centroid) and calls
  the Open-Meteo Historical Weather API (2016-2025) for each, saving
  frost days, chill hours, and heavy rain days (raw 10-year totals plus
  per-year figures) as `subzone_climate_risk` — see
  `docs/methodology.md` ("Climate risk ingestion (business question
  5)"). Unaffected by the Whakatane District scope expansion (not one of
  the 5 named subzones this script keys on), so it wasn't re-run when
  Whakatane was added.
- `08_regional_summary_expansion.py` — scoring. Two parts: (1) groups all
  21,491 scored parcels into suitability levels region-wide (not just
  the 5 named subzones) — Excellent 76.4%, Good 18.1%, Marginal 5.5% —
  saved as `suitability_levels_summary`; (2) filters to
  suitability_score >= 8.0 AND not already LCDB-classified as orchard/
  vineyard/perennial crop, saved as `expansion_candidates` — 13,041
  parcels (79.5% of the Excellent tier). Same `right=False` boundary fix
  as `05_subzone_summary.py`. See `docs/methodology.md` ("Regional
  summary and expansion candidates (business questions 1 and 2)").

All ingestion, joining, scoring, and cross-project comparison work for
Fase 2/3 is now in place. Fase 4 (insights) and Fase 5 (Streamlit
dashboard) are still to be started.
