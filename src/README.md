# Source code

Reusable production code: data loading, the scoring model, and
geospatial utilities.

## Status

Three scripts so far, all following the Python header standard in
`docs/conventions.md`:

- `00_explore_volumes.py` — exploratory, not the ingestion pipeline. No
  database writes. Confirms real data volume and geometry complexity for
  LINZ (122657), the four S-map layers, and LCDB (123148); validates the
  1 ha area threshold against the actual parcel distribution; and
  documents the LRIS WFS `bbox`/`CQL_FILTER` quirk (see
  `docs/data_sources.md`).
- `01_ingest_linz.py` — production ingestion. Fetches LINZ Property
  Boundaries server-side filtered to the 3 target TAs + 1 ha area
  threshold, saves `data/processed/parcels_linz.geojson` (14,265
  parcels).
- `02_ingest_soil_lcdb.py` — production ingestion. Computes a centroid
  per parcel, spatial-joins the four S-map layers and LCDB, and saves the
  result as `parcel_attributes` in `data/processed/terroir.db`
  (SQLite) — 99%+ match rate, see `docs/methodology.md` ("Handling
  unmatched parcels (nulls)").

Climate (Open-Meteo) ingestion and the scoring model are still to be
added.
