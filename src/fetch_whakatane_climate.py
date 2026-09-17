# =============================================================================
# TERROIR — Whakatane District climate risk (Open-Meteo), standalone
# Script: fetch_whakatane_climate.py
# Stage:  Ingestion (standalone companion, not part of the numbered order)
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Standalone companion to ingest_climate_risk.py, for Whakatane District,
which isn't one of Apophenia's 5 named subzones and so was never
covered by that script's ingestion run.

Imports fetch_hourly_weather() and compute_climate_risk() directly from
ingest_climate_risk.py rather than duplicating them, so this always
uses the exact same methodology (same date range, same frost/chill/
heavy-rain thresholds, same Open-Meteo endpoint) with no risk of
drifting out of sync if that script's methodology ever changes.

The only difference from ingest_climate_risk.py's own 5 subzone points:
the representative point here is the simple average of the centroid of
every one of Whakatane District's 5,434 parcels in
parcels_linz.geojson (computed once, hardcoded below — Whakatane isn't
one of the 5 named subzone values ingest_subzones.py assigns, so
ingest_climate_risk.py's load_subzone_points() has no row for it to
average).

Appends a "Whakatane District" row to
data/powerbi_export/subzone_climate_risk.csv — deliberately the CSV
export, not the subzone_climate_risk table in terroir.db: that table
is keyed on the 5 named Apophenia subzones only (subzone_summary.py
and cross_project_comparison.py both join on those 5 names), so
Whakatane District has no home there. The dashboard's Climate Risk
page and this CSV are the only places Whakatane's climate figures are
shown.

Not part of the numbered pipeline in src/README.md: it needs outbound
internet access, which the sandboxed shell used to build and verify
the rest of this pipeline doesn't have. Run it from a normal terminal
on your own machine, from the project root:

    python src/fetch_whakatane_climate.py
"""

import csv
import logging
import pathlib

from config import DATA_DIR, configure_logging
from ingest_climate_risk import compute_climate_risk, fetch_hourly_weather

logger = logging.getLogger(__name__)

# Representative point for Whakatane District: simple average of the
# centroid of every one of its 5,434 parcels in parcels_linz.geojson.
WHAKATANE_LAT = -38.077226
WHAKATANE_LON = 176.869339

OUT_CSV = DATA_DIR / "powerbi_export" / "subzone_climate_risk.csv"

FIELDNAMES = [
    "subzone", "lat", "lon",
    "frost_days", "frost_days_per_year",
    "chill_hours_annual_avg",
    "heavy_rain_days", "heavy_rain_days_per_year",
]


def append_whakatane_row(out_csv: pathlib.Path, row: dict) -> None:
    """Appends `row` to out_csv, writing the header first if the file
    doesn't exist yet. Kept separate from main() so it's testable
    without a live API call — see tests/test_fetch_whakatane_climate.py.
    """
    file_exists = out_csv.exists()
    with open(out_csv, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main() -> None:
    logger.info(
        f"Fetching Open-Meteo history for Whakatane District "
        f"({WHAKATANE_LAT:.4f}, {WHAKATANE_LON:.4f})..."
    )
    hourly = fetch_hourly_weather(WHAKATANE_LAT, WHAKATANE_LON)
    logger.info(f"  {len(hourly):,} hourly records fetched")

    risk = compute_climate_risk(hourly)
    row = {
        "subzone": "Whakatane District",
        "lat": WHAKATANE_LAT,
        "lon": WHAKATANE_LON,
        **risk,
    }
    logger.info("Result:")
    for key, value in row.items():
        logger.info(f"  {key}: {value}")

    append_whakatane_row(OUT_CSV, row)
    logger.info(f"Appended to {OUT_CSV}")

    assert OUT_CSV.exists(), (
        f"Expected output CSV {OUT_CSV} not found — check path"
    )


if __name__ == "__main__":
    configure_logging()
    main()
