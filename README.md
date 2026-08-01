# Terroir

Geospatial land suitability analysis for Bay of Plenty horticulture — the
sister project to Apophenia™ (Gabriela Olivera's kiwifruit export risk
simulator, already deployed).

## Objective

Analyse soil suitability and territorial risk at subzone level for Bay of
Plenty horticulture, combining cadastral, soil, and climate data. Where
Apophenia models regional climate-logistics risk, Terroir focuses on
land-level suitability — the aim is to demonstrate genuine geospatial
analysis (real shapefiles/GeoJSON, not standalone lat/long pairs), work
across multiple public New Zealand data sources, and produce business
insight applicable to horticulture and council GIS/asset-management roles.

## Stack

- **Dashboard:** Streamlit (decision documented in `docs/methodology.md`)
- **Geospatial processing:** Python (geopandas and related tooling), SQL
- **Data sources:** LINZ Data Service, S-map (Manaaki Whenua / Landcare
  Research), and Open-Meteo for climate (NIWA was evaluated and dropped
  in favour of Open-Meteo — see `docs/data_sources.md`)

## Status

Fase 0 (data source investigation) and Fase 1 (business questions) are
complete — see `docs/data_sources.md` and `docs/business_questions.md`.
Fase 2 (data ingestion) is complete for parcels + soil + LCDB + subzones:
17,400 LINZ parcels across all 3 target TAs (Tauranga City, Western Bay
of Plenty District, Ōpōtiki District — 1 ha area threshold) joined to
S-map, LCDB, and Apophenia-subzone attributes. Fase 3 (scoring) is now
implemented: 16,447 parcels scored on a weighted soil suitability
formula, grouped into Excellent/Good/Marginal levels — see
`src/README.md` and `docs/methodology.md`. Climate (Open-Meteo)
ingestion is still to be added. No notebooks, dashboard, or case study
content exist yet.

## How to run

To be documented once the data pipeline and Streamlit app exist.
