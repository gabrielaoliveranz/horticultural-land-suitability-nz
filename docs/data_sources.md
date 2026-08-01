# Data Sources

This document tracks the external data sources used in Terroir, how each is
accessed, and any licensing or access notes relevant to reproducing this
project.

**Status:** Fase 0 data source investigation complete — all three sources
confirmed.

---

## 1. LINZ Data Service (data.linz.govt.nz)

**Purpose:** Cadastral boundaries, property parcels, topography, elevation
for the Bay of Plenty study area.

**Access method:** WFS 2.0.0 — tested hands-on (GetCapabilities and
GetFeature both confirmed working) with an API key.

**Layer confirmed:** 122657 — NZ Property Boundaries.

**Auth:** API key, stored in `.env` as `LINZ_API_KEY`.

**Geographic filter:** `CQL_FILTER` on `territorial_authority_ascii IN
('Tauranga City','Western Bay of Plenty District','Opotiki District')` —
matches the geographic footprint of Apophenia's five corridors. Filters
on `territorial_authority_ascii`, not `territorial_authority` — see
"Technical note (macrons)" below.

**Parcel counts (server-side CQL, 3 TAs + area > 10,000 m² / 1 ha):**
17,400 total — Western Bay of Plenty District 11,028, Tauranga City
3,237, Ōpōtiki District 3,135. See `docs/methodology.md`, "Parcel
selection: area threshold + LCDB as attribute, not filter" for the
full area-threshold reasoning.

**Licence:** Creative Commons Attribution 3.0 New Zealand (CC-BY) for most
layers — free to use, requires attribution.

**Status:** CONFIRMED. WFS access and API key tested and working.

**Elevation/DEM:** investigated as a possible waterlogging-risk input and
deliberately excluded from the current scope — see `docs/methodology.md`
("Waterlogging risk: drainage-only proxy (DEM excluded)") for the
reasoning. Not ruled out as a v2 extension.

**Technical note (macrons):** Official NZ place names may include macrons
(e.g. Ōpōtiki) that differ from plain-ASCII spellings. Exact-string filters
using the macron field will silently return zero matches for names typed
without it. LINZ/LRIS layers generally expose an `_ascii` companion field —
always filter on that field, never hardcode a plain-ASCII name expecting it
to match. This caused 01_ingest_linz.py to silently exclude all of Opotiki
District from ingestion since the first Fase 2 run.

---

## 2. S-map (Manaaki Whenua — Landcare Research)

**Purpose:** Soil type, depth, drainage class, texture, and classification
data for the study area.

**Access method:** LRIS Portal (lris.scinfo.org.nz), not S-map Online —
S-map Online is a limited viewer only. Same Koordinates account login as
LINZ, but a separate API key is required. WFS 2.0.0 — tested hands-on and
confirmed working.

**Auth:** API key, stored in `.env` as `LRIS_API_KEY`.

**Layers confirmed (August 2025, current versions — not the deprecated
August 2024 versions):**
- 122758 — S-map Soil Depth
- 122760 — S-map Soil Texture
- 122764 — S-map Soil Drainage
- 122765 — S-map Soil Classification (soil order)

**Water holding capacity (PAW):** not freely available as a standalone
layer — it sits within the restricted "Base Property Data", under the same
commercial-use restriction as the primary soil classification layer.
**Decision:** use texture combined with drainage as a proxy for water
retention instead.

**Note for future reference:** FSL (Fundamental Soils Layers) is a
different, older (1990s) dataset in the same LRIS catalogue whose
abstracts reference "S-map" as a cross-recommendation — always verify by
the `<Title>` field starting with "S-map", not by keyword search alone.

**Licence:** Open licence for the four confirmed layers; the restricted
Base Property Data layer carries a non-commercial / non-derivative
condition (see note above).

**Status:** CONFIRMED. WFS access, API key, and all four soil attribute
layers tested and working.

**Technical note (LRIS WFS):** `bbox` and `CQL_FILTER` cannot be used
together in the same request (returns a 500 "mutually exclusive" error).
When both a spatial extent and an attribute filter are needed, fold the
bbox into the CQL as `BBOX(field, minx, miny, maxx, maxy, 'CRS84')` —
the CRS argument is required, or the query silently returns zero rows.

**Technical note (CRS mismatch):** LINZ and LRIS WFS responses default to
their source CRS, not WGS84 — LINZ returns EPSG:4167 (NZGD2000), LRIS/S-map/
LCDB return EPSG:2193 (NZTM2000, metres). Mixing these with WGS84 geometry
(e.g. centroids) causes spatial joins to silently return 0% matches, not an
error. Fix: always request `srsName=urn:ogc:def:crs:EPSG::4326` explicitly
in the WFS request, and verify against the response's own declared `crs`
field rather than assuming.

---

## 3. NIWA / Open-Meteo (Climate) — DECISION: Open-Meteo only, NIWA dropped

**Note:** NIWA merged with GNS Science on 1 July 2025 to form Earth Sciences
New Zealand. Relevant if referencing this source elsewhere in the project.

**Decision:** Terroir uses Open-Meteo exclusively for all climate variables.
NIWA/DataHub was evaluated and rejected — it offers no coverage Open-Meteo
lacks, while adding account setup, request-based access for recent data, and
no date-range filtering on downloads.

**Access method:** Open-Meteo Historical Weather API (ERA5/ERA5-Land
reanalysis). REST/JSON, no API key, no account required.

**Data used:**
- Rainfall — hourly/daily precipitation, direct from API
- Frost risk — daily minimum temperature, direct from API
- Chill hours — NOT a direct API field; calculated from hourly
  `temperature_2m` (hours below 7°C threshold during dormancy period)

**Licence:** CC BY 4.0, free for non-commercial use.

**Status:** Confirmed, decision locked per conventions.md Fase 0 rule.

---

## Open questions to resolve during hands-on exploration

- [x] Confirm exact LINZ layer(s) needed for Bay of Plenty subzone boundaries
      — layer 122657 (NZ Property Boundaries), filtered via CQL_FILTER on
      `territorial_authority`
- [x] Confirm which S-map soil attributes are available via API vs. requiring
      manual download from S-map Online / LRIS Portal — depth, texture,
      drainage, and classification confirmed via LRIS WFS; PAW is restricted,
      texture + drainage used as a proxy instead
- [x] Decide the NIWA vs. Open-Meteo split for climate variables — Open-Meteo
      only; NIWA/DataHub evaluated and dropped (no coverage gap, more access
      friction)
- [ ] Confirm attribution requirements for each source and add them to
      `docs/attributions.md` as each is first used
