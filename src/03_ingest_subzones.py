# =============================================================================
# TERROIR — Subzone assignment (NZ Suburbs and Localities)
# Script: 03_ingest_subzones.py
# Stage:  Ingestion
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Loads parcel centroids from data/processed/parcels_linz.geojson (same
approach as 02_ingest_soil_lcdb.py), fetches LINZ layer 113764 (NZ Suburbs
and Localities) bbox-filtered to the Bay of Plenty extent, and spatial-
joins (predicate="within") to derive each parcel's Apophenia subzone:

  - major_name == "Tauranga"                    -> "Tauranga"
  - name in {Katikati, Te Puke, Pongakawa,
    Opotiki}                                     -> that name
  - anything else                                -> NULL (not one of the
    5 Apophenia subzones — reported, not forced)

Adds a `subzone` column to the existing `parcel_attributes` table in
data/processed/terroir.db via an SQL UPDATE keyed on source_id — the
table is not rebuilt.

Key note (see 02_ingest_soil_lcdb.py's docstring for the full story):
parcel_id is NOT unique (only 11,936 of 14,265 values are — a fact this
script's row count surfaced during development). source_id is the real
unique key and is what every join/update here uses; parcel_id is only
carried through as a reference column.

CRS note (same lesson as 02_ingest_soil_lcdb.py): explicitly requests
srsName=EPSG:4326 and verifies it against the response's own declared
`crs` field rather than assuming.

Naming note: layer 113764's `name` field uses macrons for te reo place
names (e.g. "Ōpōtiki", not "Opotiki") — confirmed via a live sample
before writing this script. Matching against the literal ASCII string
"Opotiki" would have silently matched zero parcels. The layer's
`name_ascii` field is used instead for exactly this reason.
"""

import os
import sqlite3
from pathlib import Path

import geopandas
import numpy as np
import requests
from dotenv import load_dotenv

load_dotenv()

LINZ_API_KEY = os.environ["LINZ_API_KEY"]
LINZ_WFS_BASE = f"https://data.linz.govt.nz/services;key={LINZ_API_KEY}/wfs"

LAYER_ID = 113764
PAGE_SIZE = 1000
REQUEST_TIMEOUT = 120
EXPECTED_CRS = "EPSG::4326"

# Bay of Plenty bounding box — same extent used and documented throughout
# Fase 2 (src/00_explore_volumes.py, src/02_ingest_soil_lcdb.py).
BOP_BBOX_COORDS = (175.7, -38.2, 177.4, -37.2)
BOP_BBOX = "{},{},{},{},urn:ogc:def:crs:OGC:1.3:CRS84".format(*BOP_BBOX_COORDS)

TAURANGA_MAJOR_NAME = "Tauranga"
# Matched against name_ascii, not name — see module docstring.
TARGET_LOCALITIES = ("Katikati", "Te Puke", "Pongakawa", "Opotiki")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARCELS_PATH = PROJECT_ROOT / "data" / "processed" / "parcels_linz.geojson"
OUTPUT_DB = PROJECT_ROOT / "data" / "processed" / "terroir.db"
TABLE_NAME = "parcel_attributes"


def load_parcel_centroids(path):
    parcels = geopandas.read_file(path)
    centroids = parcels.to_crs(2193).geometry.centroid.to_crs(4326)
    return geopandas.GeoDataFrame(
        {"source_id": parcels["source_id"], "parcel_id": parcels["parcel_id"]},
        geometry=centroids, crs=4326,
    )


def fetch_localities(base_url, layer_id, bbox, page_size=PAGE_SIZE):
    features = []
    start_index = 0
    while True:
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": f"layer-{layer_id}",
            "outputFormat": "json",
            "bbox": bbox,
            "count": page_size,
            "startIndex": start_index,
            "srsName": "urn:ogc:def:crs:EPSG::4326",
        }
        response = requests.get(base_url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        payload = response.json()

        declared_crs = payload.get("crs", {}).get("properties", {}).get("name", "")
        if EXPECTED_CRS not in declared_crs:
            raise ValueError(
                f"Expected {EXPECTED_CRS} but WFS response declared crs="
                f"{declared_crs!r} — do not trust unverified coordinates."
            )

        page = payload.get("features", [])
        features.extend(page)
        if len(page) < page_size:
            break
        start_index += page_size

    return geopandas.GeoDataFrame.from_features(features, crs=4326)


def derive_subzone(joined):
    conditions = [
        joined["major_name"] == TAURANGA_MAJOR_NAME,
        joined["name_ascii"].isin(TARGET_LOCALITIES),
    ]
    choices = [
        TAURANGA_MAJOR_NAME,
        joined["name_ascii"],
    ]
    return np.select(conditions, choices, default=None)


def report_subzones(result):
    total = len(result)
    print(f"\nSubzone assignment (of {total:,} parcels):")
    counts = result["subzone"].value_counts(dropna=True).sort_values(ascending=False)
    for subzone, n in counts.items():
        print(f"  {subzone}: {n:,} ({n / total * 100:.1f}%)")

    n_null = result["subzone"].isna().sum()
    print(f"  NULL (outside the 5 Apophenia subzones): {n_null:,} ({n_null / total * 100:.1f}%)")


def update_subzone_column(db_path, table_name, result):
    with sqlite3.connect(db_path) as conn:
        existing_cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})")]
        if "subzone" not in existing_cols:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN subzone TEXT")

        result[["source_id", "subzone"]].to_sql("subzone_lookup", conn, if_exists="replace", index=False)
        conn.execute(
            f"""
            UPDATE {table_name}
            SET subzone = (
                SELECT subzone FROM subzone_lookup
                WHERE subzone_lookup.source_id = {table_name}.source_id
            )
            """
        )
        conn.execute("DROP TABLE subzone_lookup")
        conn.commit()


def main():
    print(f"Loading parcel centroids from {PARCELS_PATH}...")
    centroids = load_parcel_centroids(PARCELS_PATH)
    print(f"  {len(centroids):,} parcel centroids computed")

    print(f"\nFetching LINZ layer {LAYER_ID} (NZ Suburbs and Localities)...")
    localities = fetch_localities(LINZ_WFS_BASE, LAYER_ID, BOP_BBOX)
    print(f"  {len(localities):,} localities fetched")

    joined = geopandas.sjoin(
        centroids[["source_id", "geometry"]],
        localities[["name_ascii", "major_name", "geometry"]],
        how="left",
        predicate="within",
    )
    # A centroid landing exactly on a shared boundary can match more than
    # one locality; keep the first match rather than duplicate the row.
    # Keyed on source_id (the true unique row id), not parcel_id — see
    # module docstring.
    joined = joined.drop_duplicates(subset="source_id", keep="first")

    joined["subzone"] = derive_subzone(joined)
    result = joined[["source_id", "subzone"]].reset_index(drop=True)

    report_subzones(result)

    update_subzone_column(OUTPUT_DB, TABLE_NAME, result)
    print(f"\nUpdated 'subzone' column on table '{TABLE_NAME}' in {OUTPUT_DB}")

    assert OUTPUT_DB.exists(), f"Expected output db {OUTPUT_DB} not found — check path"


if __name__ == "__main__":
    main()
