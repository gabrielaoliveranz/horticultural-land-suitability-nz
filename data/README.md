# Data

Holds all data used in the Terroir analysis, organised into raw,
processed, and external sources.

## Status

Source access confirmed for all evaluated sources (Fase 0 complete) —
LINZ and S-map confirmed via WFS, NIWA evaluated and dropped in favour
of Open-Meteo. See `docs/data_sources.md`. Ingestion (Fase 2) and
scoring (Fase 3) are both complete: `processed/` holds
`parcels_linz.geojson` and `terroir.db` (7 tables), `external/` holds
the one Apophenia corridor CSV used for the cross-project comparison —
see each subfolder's own README for detail. `raw/` stays empty by
design (see below), not because ingestion hasn't happened.

## Structure

- `raw/` — unmodified downloads, organised by source (`linz/`, `smap/`,
  `lcdb/`, `open-meteo/`, `niwa/` — the last of these documents a
  rejected source, see its README)
- `processed/` — cleaned, joined datasets ready for analysis
- `external/` — supplementary reference datasets (e.g. Stats NZ)
