# Source code

Reusable production code: data loading, the scoring model, and
geospatial utilities.

## Status

Contains `00_explore_volumes.py` — an exploratory script, not the
ingestion pipeline. No database writes. Confirms real data volume and
geometry complexity for LINZ (122657), the four S-map layers, and LCDB
(123148); validates the 1 ha area threshold against the actual parcel
distribution; and documents the LRIS WFS `bbox`/`CQL_FILTER` quirk (see
`docs/data_sources.md`). Results feed `docs/methodology.md`.

The real ingestion scripts (Fase 2 proper) are about to be added. Every
file, exploratory or production, follows the Python header standard in
`docs/conventions.md`.
