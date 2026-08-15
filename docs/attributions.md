# Attributions

Log of third-party assets (icons, images, datasets) used in this
project, recorded at the time each is downloaded or used — not
reconstructed from memory later — per `docs/conventions.md`.

Format:

```markdown
- <Asset name> by <Author> — <Source> (<URL>)
```

## Log

- NZ Property Boundaries by Toitū Te Whenua Land Information New Zealand (LINZ) — LINZ Data Service (https://data.linz.govt.nz/layer/122657-nz-property-boundaries/), CC-BY 3.0 New Zealand

- S-map Soil Depth (Aug 2025) by Manaaki Whenua – Landcare Research — LRIS Portal (https://lris.scinfo.org.nz/layer/122758-s-map-soil-depth-aug-2025/)

- S-map Soil Texture (Aug 2025) by Manaaki Whenua – Landcare Research — LRIS Portal (https://lris.scinfo.org.nz/layer/122760-s-map-soil-texture-aug-2025/)

- S-map Soil Drainage (Aug 2025) by Manaaki Whenua – Landcare Research — LRIS Portal (https://lris.scinfo.org.nz/layer/122764-s-map-soil-drainage-aug-2025/)

- S-map Soil Classification (soil order) (Aug 2025) by Manaaki Whenua – Landcare Research — LRIS Portal (https://lris.scinfo.org.nz/layer/122765-s-map-soil-classification-soil-order-aug-2025/)

- Historical Weather API by Open-Meteo (https://open-meteo.com/en/docs/historical-weather-api), CC BY 4.0

- LCDB v6.0 — Land Cover Database version 6.0, Mainland New Zealand by Manaaki Whenua – Landcare Research — LRIS Portal (https://lris.scinfo.org.nz/layer/123148-lcdb-v60-land-cover-database-version-60-mainland-new-zealand/), CC BY 4.0. Licence verified 2026-08-15 directly against the layer's own Koordinates API metadata (`https://lris.scinfo.org.nz/services/api/v1/layers/123148/` → `license.title` = "Creative Commons Attribution 4.0 International", `license.type` = "cc-by", `license.version` = "4.0"; human-readable at https://lris.scinfo.org.nz/license/attribution-4-0-international/) — not read off a summary or assumed to match the S-map layers above it.

- Cat icon (GitHub) by Dave Gandy — Flaticon (https://www.flaticon.es/iconos-gratis/gato)

- LinkedIn icon by Magnific — Flaticon (https://www.flaticon.es/iconos-gratis/linkedin)

- Kiwifruit icon by Park Jisun — Flaticon (https://www.flaticon.com/free-icons/kiwifruit)

## Status

LINZ, S-map, Open-Meteo, and LCDB entries logged (seven sources total),
plus three dashboard footer icons (GitHub, LinkedIn, kiwifruit — ten
entries total). NIWA was evaluated and dropped in favour of Open-Meteo
(see `docs/data_sources.md`) — no NIWA attribution needed.

LCDB was added 2026-08-15 — it was actively used (`src/ingest_soil_lcdb.py`,
`terroir.db`'s `parcel_attributes.lcdb_class_2023`) but missing from this
log despite being logged alongside the same four S-map layers it's
fetched next to in code. Its licence (CC BY 4.0) is now confirmed
directly against the layer's own API metadata, not assumed to match
S-map's — see the log entry above.
