# Data

Holds all data used in the Terroir analysis, organised into raw,
processed, and external sources.

## Status

Source access confirmed for all evaluated sources (Fase 0 complete) —
LINZ and S-map confirmed via WFS, NIWA evaluated and dropped in favour
of Open-Meteo. See `docs/data_sources.md`. No data has actually been
ingested into this folder yet — that's Fase 2, not started.

## Structure

- `raw/` — unmodified downloads, organised by source (`linz/`, `smap/`,
  `lcdb/`, `open-meteo/`, `niwa/` — the last of these documents a
  rejected source, see its README)
- `processed/` — cleaned, joined datasets ready for analysis
- `external/` — supplementary reference datasets (e.g. Stats NZ)
