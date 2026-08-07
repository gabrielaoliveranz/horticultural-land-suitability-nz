# =============================================================================
# TERROIR — Subzone assignment (NZ Suburbs and Localities)
# Script: ingest_subzones.py
# Stage:  Ingestion
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Loads parcel centroids from data/processed/parcels_linz.geojson (same
approach as ingest_soil_lcdb.py), fetches LINZ layer 113764 (NZ Suburbs
and Localities) bbox-filtered to the Bay of Plenty extent, and spatial-
joins (predicate="within") to derive each parcel's Apophenia subzone:

  - major_name_ascii == "Tauranga"               -> "Tauranga"
  - name_ascii in {Katikati, Te Puke, Pongakawa,
    Opotiki}                                     -> that name
  - anything else                                -> NULL (not one of the
    5 Apophenia subzones — reported, not forced)

Adds a `subzone` column to the existing `parcel_attributes` table in
data/processed/terroir.db via an SQL UPDATE keyed on source_id — the
table is not rebuilt.

Key note (see ingest_soil_lcdb.py's docstring for the full story):
parcel_id is NOT unique (only 11,936 of 14,265 values are — a fact this
script's row count surfaced during development). source_id is the real
unique key and is what every join/update here uses; parcel_id is only
carried through as a reference column.

CRS note (same lesson as ingest_soil_lcdb.py): explicitly requests
srsName=EPSG:4326 and verifies it against the response's own declared
`crs` field rather than assuming.

Naming note (macron-safe on both branches): layer 113764's `name` and
`major_name` fields use official macron spelling for te reo place names
(e.g. "Ōpōtiki", not "Opotiki") — confirmed via a live sample. This bit
twice: first caught for the locality-name branch (fixed by matching
name_ascii instead of name), then the major_name == "Tauranga" branch
turned out to only work by coincidence, since "Tauranga" itself has no
macron — the same trap was latent there too. Both branches now match
against the `_ascii` companion fields (name_ascii, major_name_ascii)
consistently, per docs/data_sources.md, "Technical note (macrons)".

Bbox note: widened from the original (175.7, -38.2, 177.4, -37.2) to
(175.7, -38.9, 178.2, -37.2) — see ingest_soil_lcdb.py's docstring.
The original box was sized before Opotiki District was correctly
included in the dataset (see ingest_linz.py) and would have missed
the Ōpōtiki locality/suburb polygons this script depends on.
"""

import logging
import os
from pathlib import Path

import geopandas
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

from config import DB_PATH, PARCELS_PATH, configure_logging, get_connection

logger = logging.getLogger(__name__)

load_dotenv()

LINZ_API_KEY = os.environ["LINZ_API_KEY"]
LINZ_WFS_BASE = f"https://data.linz.govt.nz/services;key={LINZ_API_KEY}/wfs"

LAYER_ID = 113764
PAGE_SIZE = 1000
REQUEST_TIMEOUT = 120
EXPECTED_CRS = "EPSG::4326"

# Bay of Plenty bounding box (Katikati to East Cape) — same widened
# extent as src/ingest_soil_lcdb.py; see module docstring's bbox note.
BOP_BBOX_COORDS = (175.7, -38.9, 178.2, -37.2)
BOP_BBOX = "{},{},{},{},urn:ogc:def:crs:OGC:1.3:CRS84".format(*BOP_BBOX_COORDS)

TAURANGA_MAJOR_NAME = "Tauranga"
# Matched against name_ascii / major_name_ascii, not name / major_name —
# see module docstring's naming note.
TARGET_LOCALITIES = ("Katikati", "Te Puke", "Pongakawa", "Opotiki")

TABLE_NAME = "parcel_attributes"


def load_parcel_centroids(path: Path) -> geopandas.GeoDataFrame:
    parcels = geopandas.read_file(path)
    centroids = parcels.to_crs(2193).geometry.centroid.to_crs(4326)
    return geopandas.GeoDataFrame(
        {
            "source_id": parcels["source_id"],
            "parcel_id": parcels["parcel_id"],
        },
        geometry=centroids, crs=4326,
    )


def fetch_localities(
    base_url: str, layer_id: int, bbox: str, page_size: int = PAGE_SIZE
) -> geopandas.GeoDataFrame:
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
        response = requests.get(
            base_url, params=params, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        payload = response.json()

        declared_crs = (
            payload.get("crs", {}).get("properties", {}).get("name", "")
        )
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


def derive_subzone(joined: pd.DataFrame) -> np.ndarray:
    conditions = [
        joined["major_name_ascii"] == TAURANGA_MAJOR_NAME,
        joined["name_ascii"].isin(TARGET_LOCALITIES),
    ]
    choices = [
        TAURANGA_MAJOR_NAME,
        joined["name_ascii"],
    ]
    return np.select(conditions, choices, default=None)


def report_subzones(result: pd.DataFrame) -> None:
    total = len(result)
    logger.info(f"Subzone assignment (of {total:,} parcels):")
    counts = (
        result["subzone"].value_counts(dropna=True)
        .sort_values(ascending=False)
    )
    for subzone, n in counts.items():
        logger.info(f"  {subzone}: {n:,} ({n / total * 100:.1f}%)")

    n_null = result["subzone"].isna().sum()
    logger.info(
        f"  NULL (outside the 5 Apophenia subzones): {n_null:,} "
        f"({n_null / total * 100:.1f}%)"
    )


def update_subzone_column(
    db_path: Path, table_name: str, result: pd.DataFrame
) -> None:
    with get_connection(db_path) as conn:
        existing_cols = [
            row[1]
            for row in conn.execute(f"PRAGMA table_info({table_name})")
        ]
        if "subzone" not in existing_cols:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN subzone TEXT")

        result[["source_id", "subzone"]].to_sql(
            "subzone_lookup", conn, if_exists="replace", index=False
        )
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


def main() -> None:
    logger.info(f"Loading parcel centroids from {PARCELS_PATH}...")
    centroids = load_parcel_centroids(PARCELS_PATH)
    logger.info(f"  {len(centroids):,} parcel centroids computed")

    logger.info(
        f"Fetching LINZ layer {LAYER_ID} (NZ Suburbs and Localities)..."
    )
    localities = fetch_localities(LINZ_WFS_BASE, LAYER_ID, BOP_BBOX)
    logger.info(f"  {len(localities):,} localities fetched")

    joined = geopandas.sjoin(
        centroids[["source_id", "geometry"]],
        localities[["name_ascii", "major_name_ascii", "geometry"]],
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

    update_subzone_column(DB_PATH, TABLE_NAME, result)
    logger.info(
        f"Updated 'subzone' column on table '{TABLE_NAME}' in {DB_PATH}"
    )

    assert DB_PATH.exists(), (
        f"Expected output db {DB_PATH} not found — check path"
    )


if __name__ == "__main__":
    configure_logging()
    main()
