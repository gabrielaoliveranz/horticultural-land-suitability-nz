# Raw data — S-map

Raw, unmodified downloads from S-map (Manaaki Whenua / Landcare
Research), accessed via the LRIS Portal (lris.scinfo.org.nz), not S-map
Online.

## Access

Confirmed — WFS 2.0.0, tested working. Four layers confirmed (August
2025, current versions): 122758 (Soil Depth), 122760 (Soil Texture),
122764 (Soil Drainage), 122765 (Soil Classification / soil order). API
key stored in `.env` as `LRIS_API_KEY`. Full detail in
`docs/data_sources.md`.

## Licence

Open licence for the four confirmed layers. Water holding capacity
(PAW) sits within the restricted "Base Property Data" layer
(non-commercial / non-derivative) and is not used here — texture
combined with drainage is used as a proxy instead (see
`docs/methodology.md`). Logged in `docs/attributions.md`.

## Status

Access confirmed (Fase 0). Ingestion is complete (`src/ingest_soil_lcdb.py`,
94.1% match rate) — this folder stays empty by design, not because
ingestion hasn't happened: the pipeline fetches WFS responses live on
each run and writes straight to `parcel_attributes` in
`data/processed/terroir.db`, it never caches a raw copy here.
