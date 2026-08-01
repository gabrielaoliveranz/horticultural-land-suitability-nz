# =============================================================================
# TERROIR — Climate risk ingestion (Open-Meteo)
# Script: 07_ingest_climate_risk.py
# Stage:  Ingestion
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Computes one representative point per subzone (the average parcel centroid
of every parcel with that subzone, excluding NULL — same parcel geometry
already used in 03_ingest_subzones.py), then calls the Open-Meteo
Historical Weather API (hourly temperature_2m + precipitation,
2016-01-01 to 2025-12-31, local NZ timezone) for each of the 5 points.

Per subzone, computes:
  - Frost days: count of days where the daily minimum hourly temperature
    is < 0°C, total across the full 2016-2025 period, plus
    frost_days_per_year (that total / 10).
  - Chill hours (annual average): hours where temperature_2m < 7°C during
    May-August (dormancy window), summed across all 10 years and divided
    by 10 to get a per-year figure.
  - Heavy rain days: count of days where total daily precipitation is
    > 25mm, total across the full 2016-2025 period, plus
    heavy_rain_days_per_year (that total / 10).

Both the raw 10-year totals and the per-year figures are kept side by
side: the raw counts are useful context (e.g. "2 frost days in 10
years"), while future scoring uses the per-year columns so all 3 climate
metrics are on the same annual basis as each other.

Saves the result as `subzone_climate_risk` in data/processed/terroir.db
and prints the summary table.
"""

import sqlite3
from pathlib import Path

import geopandas
import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARCELS_PATH = PROJECT_ROOT / "data" / "processed" / "parcels_linz.geojson"
DB_PATH = PROJECT_ROOT / "data" / "processed" / "terroir.db"
ATTRIBUTES_TABLE = "parcel_attributes"
CLIMATE_TABLE = "subzone_climate_risk"

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
START_DATE = "2016-01-01"
END_DATE = "2025-12-31"
N_YEARS = 10  # 2016-2025 inclusive
REQUEST_TIMEOUT = 180
TIMEZONE = "Pacific/Auckland"

FROST_THRESHOLD_C = 0.0
CHILL_THRESHOLD_C = 7.0
CHILL_MONTHS = (5, 6, 7, 8)  # May-August dormancy window
HEAVY_RAIN_THRESHOLD_MM = 25.0


def load_subzone_points(parcels_path, db_path):
    parcels = geopandas.read_file(parcels_path)
    with sqlite3.connect(db_path) as conn:
        attributes = pd.read_sql(
            f"SELECT source_id, subzone FROM {ATTRIBUTES_TABLE} WHERE subzone IS NOT NULL",
            conn,
        )

    merged = parcels.merge(attributes, on="source_id", how="inner")

    # Averaged in a projected CRS (NZTM2000) for accuracy, then the single
    # averaged point per subzone is converted back to WGS84 for the
    # Open-Meteo API, which expects lat/lon.
    projected = merged.to_crs(2193)
    merged["cx"] = projected.geometry.centroid.x
    merged["cy"] = projected.geometry.centroid.y

    avg = merged.groupby("subzone")[["cx", "cy"]].mean().reset_index()
    avg_points = geopandas.GeoDataFrame(
        avg, geometry=geopandas.points_from_xy(avg["cx"], avg["cy"]), crs=2193,
    ).to_crs(4326)
    avg_points["lon"] = avg_points.geometry.x
    avg_points["lat"] = avg_points.geometry.y

    return avg_points[["subzone", "lon", "lat"]]


def fetch_hourly_weather(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": "temperature_2m,precipitation",
        "timezone": TIMEZONE,
    }
    response = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    hourly = response.json()["hourly"]

    df = pd.DataFrame({
        "time": pd.to_datetime(hourly["time"]),
        "temperature_2m": hourly["temperature_2m"],
        "precipitation": hourly["precipitation"],
    })
    df["date"] = df["time"].dt.date
    df["month"] = df["time"].dt.month
    return df


def compute_climate_risk(hourly):
    daily_min_temp = hourly.groupby("date")["temperature_2m"].min()
    frost_days = int((daily_min_temp < FROST_THRESHOLD_C).sum())

    dormancy = hourly[hourly["month"].isin(CHILL_MONTHS)]
    chill_hours_total = int((dormancy["temperature_2m"] < CHILL_THRESHOLD_C).sum())
    chill_hours_annual_avg = round(chill_hours_total / N_YEARS, 1)

    daily_precip = hourly.groupby("date")["precipitation"].sum()
    heavy_rain_days = int((daily_precip > HEAVY_RAIN_THRESHOLD_MM).sum())

    return {
        "frost_days": frost_days,
        "frost_days_per_year": round(frost_days / N_YEARS, 1),
        "chill_hours_annual_avg": chill_hours_annual_avg,
        "heavy_rain_days": heavy_rain_days,
        "heavy_rain_days_per_year": round(heavy_rain_days / N_YEARS, 1),
    }


def print_summary(results):
    headers = [
        "Subzone", "Lat", "Lon",
        "Frost (10yr)", "Frost/yr",
        "Chill hrs/yr",
        "Heavy rain (10yr)", "Heavy rain/yr",
    ]
    widths = [12, 10, 10, 13, 9, 13, 18, 14]

    def fmt_row(values):
        return "  ".join(str(v).ljust(w) for v, w in zip(values, widths))

    print()
    print(fmt_row(headers))
    print("  ".join("-" * w for w in widths))
    for row in results:
        print(fmt_row([
            row["subzone"],
            f"{row['lat']:.4f}",
            f"{row['lon']:.4f}",
            row["frost_days"],
            row["frost_days_per_year"],
            row["chill_hours_annual_avg"],
            row["heavy_rain_days"],
            row["heavy_rain_days_per_year"],
        ]))
    print()


def main():
    print(f"Computing representative point per subzone from {PARCELS_PATH}...")
    points = load_subzone_points(PARCELS_PATH, DB_PATH)
    print(f"  {len(points)} subzone points computed")

    results = []
    for _, point in points.iterrows():
        subzone, lat, lon = point["subzone"], point["lat"], point["lon"]
        print(f"\nFetching Open-Meteo history for {subzone} ({lat:.4f}, {lon:.4f})...")
        hourly = fetch_hourly_weather(lat, lon)
        print(f"  {len(hourly):,} hourly records ({START_DATE} to {END_DATE})")

        risk = compute_climate_risk(hourly)
        results.append({"subzone": subzone, "lat": lat, "lon": lon, **risk})

    print_summary(results)

    result_df = pd.DataFrame(results)
    with sqlite3.connect(DB_PATH) as conn:
        result_df.to_sql(CLIMATE_TABLE, conn, if_exists="replace", index=False)
        conn.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{CLIMATE_TABLE}_subzone "
            f"ON {CLIMATE_TABLE}(subzone)"
        )

    print(f"Saved {len(result_df)} rows to table '{CLIMATE_TABLE}' in {DB_PATH}")

    assert DB_PATH.exists(), f"Expected output db {DB_PATH} not found — check path"


if __name__ == "__main__":
    main()
