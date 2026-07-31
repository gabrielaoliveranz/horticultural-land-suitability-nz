# =============================================================================
# TERROIR — LINZ Property Boundaries ingestion
# Script: 01_ingest_linz.py
# Stage:  Ingestion
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Fetches LINZ layer 122657 (NZ Property Boundaries), filtered server-side
via CQL_FILTER to the 3 target territorial authorities AND area > 10,000 m2
(the 1 ha threshold locked in docs/methodology.md, "Parcel selection: area
threshold + LCDB as attribute, not filter"), and saves the result as
data/processed/parcels_linz.geojson.

Confirmed during Fase 2 exploration: this WFS rejects requests that set
both `bbox` and `cql_filter` (500 "mutually exclusive") — same quirk as
the LRIS WFS documented in docs/data_sources.md. Not an issue here since
this script only needs the attribute filter, no bbox.
"""

import os
from pathlib import Path

import geopandas
import requests
from dotenv import load_dotenv

load_dotenv()

LINZ_API_KEY = os.environ["LINZ_API_KEY"]
LINZ_WFS_BASE = f"https://data.linz.govt.nz/services;key={LINZ_API_KEY}/wfs"

LAYER_ID = 122657
PAGE_SIZE = 1000
REQUEST_TIMEOUT = 120

TERRITORIAL_AUTHORITIES = (
    "Tauranga City",
    "Western Bay of Plenty District",
    "Opotiki District",
)
AREA_THRESHOLD_M2 = 10_000

CQL_FILTER = "territorial_authority IN ({}) AND area > {}".format(
    ", ".join(f"'{ta}'" for ta in TERRITORIAL_AUTHORITIES),
    AREA_THRESHOLD_M2,
)

# Exploration (src/00_explore_volumes.py) swept area thresholds client-side
# against a fixed 109,513-parcel baseline and found ~14,265 parcels above
# 10,000 m². This run applies the same threshold server-side via CQL, so a
# small difference from that figure is expected, not a bug.
EXPECTED_ROW_COUNT_APPROX = 14_265

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
OUTPUT_PATH = OUTPUT_DIR / "parcels_linz.geojson"


def fetch_all_features(base_url, layer_id, cql_filter, page_size=PAGE_SIZE):
    features = []
    start_index = 0
    while True:
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": f"layer-{layer_id}",
            "outputFormat": "json",
            "cql_filter": cql_filter,
            "count": page_size,
            "startIndex": start_index,
        }
        response = requests.get(base_url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        page_features = response.json().get("features", [])
        features.extend(page_features)
        print(f"  fetched {len(features)} features so far...")

        if len(page_features) < page_size:
            break
        start_index += page_size

    return features


def main():
    print(f"Fetching LINZ layer {LAYER_ID} with filter:\n  {CQL_FILTER}")
    features = fetch_all_features(LINZ_WFS_BASE, LAYER_ID, CQL_FILTER)

    gdf = geopandas.GeoDataFrame.from_features(features, crs="EPSG:4326")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    gdf.to_file(OUTPUT_PATH, driver="GeoJSON")

    print(f"\nSaved {len(gdf)} parcels to {OUTPUT_PATH}")
    print(
        f"Expected approx. {EXPECTED_ROW_COUNT_APPROX:,} parcels from "
        f"exploration (client-side threshold sweep) — a small difference "
        f"from this server-side CQL filter run is expected."
    )

    assert OUTPUT_DIR.exists(), f"Expected output dir {OUTPUT_DIR} not found — check path"


if __name__ == "__main__":
    main()
