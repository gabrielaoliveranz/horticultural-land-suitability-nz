# Open-Meteo

Purpose: raw climate data pulled from the Open-Meteo Historical Weather API
— NZ's sole confirmed climate source for Terroir (NIWA was evaluated and
rejected, see data/raw/niwa/README.md).

**Access:** Open-Meteo Historical Weather API (ERA5/ERA5-Land reanalysis).
REST/JSON, no API key required. See docs/data_sources.md for full details.

**Data pulled:** hourly/daily precipitation, daily min/max temperature.
Chill hours are calculated from hourly temperature, not pulled directly
— see docs/methodology.md.

**Licence:** CC BY 4.0.

**Status:** Source confirmed (Fase 0). Ingestion is complete
(`src/ingest_climate_risk.py`, 5 subzones) — this folder stays empty
by design, not because ingestion hasn't happened: the pipeline calls
the API live on each run and writes straight to `subzone_climate_risk`
in `data/processed/terroir.db`, it never caches a raw copy here.
