# Source code

Reusable production code: data loading, the scoring model, and
geospatial utilities.

## Status

Five scripts so far, all following the Python header standard in
`docs/conventions.md`:

- `00_explore_volumes.py` — exploratory, not the ingestion pipeline. No
  database writes. Confirms real data volume and geometry complexity for
  LINZ (122657), the four S-map layers, and LCDB (123148); validates the
  1 ha area threshold against the actual parcel distribution; and
  documents the LRIS WFS `bbox`/`CQL_FILTER` quirk (see
  `docs/data_sources.md`).
- `01_ingest_linz.py` — production ingestion. Fetches LINZ Property
  Boundaries server-side filtered to the 3 target TAs + 1 ha area
  threshold, saves `data/processed/parcels_linz.geojson` (17,400
  parcels).
- `02_ingest_soil_lcdb.py` — production ingestion. Computes a centroid
  per parcel, spatial-joins the four S-map layers and LCDB, and saves the
  result as `parcel_attributes` in `data/processed/terroir.db` (SQLite)
  — 94.5% S-map match rate, 99.7% LCDB match rate, see
  `docs/methodology.md` ("Handling unmatched parcels (nulls)").
- `03_ingest_subzones.py` — production ingestion. Spatial-joins parcel
  centroids against LINZ layer 113764 (NZ Suburbs and Localities) to
  derive each parcel's Apophenia subzone (Tauranga, Katikati, Te Puke,
  Pongakawa, Opotiki), adding a `subzone` column to `parcel_attributes`
  — 23.7% of parcels fall within one of the 5 named subzones, by design
  (see `docs/methodology.md`).
- `04_calculate_score.py` — scoring. Excludes parcels with any null soil
  attribute (953 of 17,400), maps soil_order/soil_texture/soil_drainage/
  soil_depth to points and applies the weighted formula from
  `docs/methodology.md` ("Point tables", "Weights"), saving the result as
  a new `parcel_scores` table (keyed on source_id) in
  `data/processed/terroir.db` — 16,447 parcels scored.

Climate (Open-Meteo) ingestion is still to be added.
