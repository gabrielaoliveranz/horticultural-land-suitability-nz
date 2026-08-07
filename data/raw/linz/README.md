# Raw data — LINZ

Raw, unmodified downloads from the LINZ Data Service (data.linz.govt.nz).

## Access

Confirmed — WFS 2.0.0 (GetCapabilities and GetFeature tested working).
Layer 122657 (NZ Property Boundaries), filtered to Tauranga City /
Western Bay of Plenty District / Ōpōtiki District / Whakatāne District
via `CQL_FILTER` (Whakatāne added as a 4th TA after
`docs/data_sources.md`'s "Scope completeness verification" confirmed it
holds real kiwifruit land the original 3-TA footprint excluded). API
key stored in `.env` as `LINZ_API_KEY`. Full detail in
`docs/data_sources.md`.

## Licence

Creative Commons Attribution 3.0 New Zealand (CC-BY) — free to use,
requires attribution. Logged in `docs/attributions.md`.

## Status

Access confirmed (Fase 0). Ingestion is complete (`src/ingest_linz.py`,
22,834 parcels) — this folder stays empty by design, not because
ingestion hasn't happened: the pipeline fetches WFS responses live on
each run and writes straight to `data/processed/parcels_linz.geojson`,
it never caches a raw copy here.
