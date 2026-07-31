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

**Status:** Source confirmed (Fase 0). No data ingested yet — Fase 2 not
started.
