# =============================================================================
# TERROIR — Soil (S-map) and land-cover (LCDB) attribute join
# Script: ingest_soil_lcdb.py
# Stage:  Ingestion
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Loads data/processed/parcels_linz.geojson, computes one centroid per parcel,
and spatial-joins (predicate="within") each centroid against:
  - S-map layers 122758 (depth), 122760 (texture), 122764 (drainage),
    122765 (soil order)
  - LCDB layer 123148 (Name_2023 only)
all bbox-filtered to the Bay of Plenty extent defined below (see "Bbox
note" further down — this extent supersedes the narrower one originally
explored in src/explore_volumes.py).

Assembles source_id, parcel_id, soil_depth, soil_texture, soil_drainage,
soil_order, lcdb_class_2023 into one table and saves it as
`parcel_attributes` in data/processed/terroir.db (SQLite). Unmatched
parcels (no polygon at that centroid, or a null attribute) are reported
per column, not treated as a failure — some gaps are expected at
soil/land-cover coverage edges.

Data quality note (key choice): `source_id` is the row's unique key, NOT
`parcel_id`. Confirmed against the live data — only 11,936 of 14,265
`parcel_id` values are unique (468 values shared across 2,797 rows: LINZ
"Unit of Property" features such as cross-leases/unit titles that share
one underlying cadastral parcel_id but are genuinely distinct rows with
different geometry, area, and valuation_reference). `source_id` is
unique across all 14,265 rows. Joining/indexing on parcel_id silently
broadcasts one row's spatial-join result onto every other row sharing
its parcel_id — found via a mismatched row count while building
ingest_subzones.py. `parcel_id` is kept as a plain reference column,
not a key.

Data quality note (bbox): raw parcel geometry bounds are NOT used to
derive the WFS bbox. A handful of parcels are LINZ "Unit of Property"
features whose parts are scattered far outside the Bay of Plenty under
one feature — their combined bounds span almost the length of the
country. Using a documented, deliberately-sized bbox instead keeps the
S-map/LCDB fetch scoped correctly; those affected parcels are flagged by
source_id and simply come back unmatched on every attribute, which is
the correct outcome for them.

Bbox note: widened from the original (175.7, -38.2, 177.4, -37.2) to
(175.7, -38.9, 178.2, -37.2). That original box was sized against a
2-of-3-TA dataset (Opotiki District was silently excluded by a macron
bug in ingest_linz.py's CQL filter — see docs/data_sources.md,
"Technical note (macrons)"). With Opotiki District correctly included,
its real extent reaches lon 178.15 / lat -38.82 (East Cape localities
like Cape Runaway, Whanarua Bay) — the old box would have silently
under-covered ~half of Opotiki's parcels.
"""

import os
import sqlite3
from pathlib import Path

import geopandas
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

LRIS_API_KEY = os.environ["LRIS_API_KEY"]
LRIS_WFS_BASE = f"https://lris.scinfo.org.nz/services;key={LRIS_API_KEY}/wfs"

PAGE_SIZE = 1000
REQUEST_TIMEOUT = 120

# Bay of Plenty bounding box (Katikati to East Cape) — widened to cover
# all target TAs correctly (originally for Opotiki District, still
# sufficient for Whakatane District added later); see module docstring's
# "Bbox note".
BOP_BBOX_COORDS = (175.7, -38.9, 178.2, -37.2)
BOP_BBOX = "{},{},{},{},urn:ogc:def:crs:OGC:1.3:CRS84".format(*BOP_BBOX_COORDS)

# layer_id -> (source field, confirmed via sample feature; output column)
SMAP_LAYERS = {
    122758: ("SibDepth", "soil_depth"),
    122760: ("Texture", "soil_texture"),
    122764: ("Drainage", "soil_drainage"),
    122765: ("NZSCOrder", "soil_order"),
}
LCDB_LAYER_ID = 123148
LCDB_FIELD = "Name_2023"
LCDB_COLUMN = "lcdb_class_2023"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = PROJECT_ROOT / "data" / "processed" / "parcels_linz.geojson"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DB = OUTPUT_DIR / "terroir.db"
TABLE_NAME = "parcel_attributes"


def load_parcel_centroids(path):
    parcels = geopandas.read_file(path)
    # Centroid computed in a projected CRS (NZTM2000) for accuracy, then
    # converted back to WGS84 to match the WFS layers' output CRS.
    centroids = parcels.to_crs(2193).geometry.centroid.to_crs(4326)
    return geopandas.GeoDataFrame(
        {"source_id": parcels["source_id"], "parcel_id": parcels["parcel_id"]},
        geometry=centroids, crs=4326,
    )


def flag_out_of_region(centroids, bbox_coords):
    min_lon, min_lat, max_lon, max_lat = bbox_coords
    x, y = centroids.geometry.x, centroids.geometry.y
    in_region = x.between(min_lon, max_lon) & y.between(min_lat, max_lat)
    outliers = centroids.loc[~in_region]
    if len(outliers):
        print(
            f"WARNING: {len(outliers)} parcel centroid(s) fall outside the "
            f"documented Bay of Plenty extent {bbox_coords} — likely LINZ "
            f"'Unit of Property' features bundling legally distinct parcels "
            f"scattered across NZ under one feature. These will correctly "
            f"come back unmatched on every soil/LCDB attribute below:"
        )
        for _, row in outliers.iterrows():
            print(f"  source_id={row['source_id']}  parcel_id={row['parcel_id']}  centroid=({row.geometry.x:.4f}, {row.geometry.y:.4f})")
    return centroids


def fetch_layer_gdf(base_url, layer_id, bbox, page_size=PAGE_SIZE):
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
            # This WFS's native/declared CRS is EPSG:2193 (NZTM2000, metres),
            # not WGS84 — confirmed via the response's "crs" field, which
            # silently broke the sjoin below (centroids in degrees vs.
            # polygons in metres never intersect). Request explicit
            # reprojection so the output is truly EPSG:4326.
            "srsName": "urn:ogc:def:crs:EPSG::4326",
        }
        response = requests.get(base_url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        page = response.json().get("features", [])
        features.extend(page)

        if len(page) < page_size:
            break
        start_index += page_size

    return geopandas.GeoDataFrame.from_features(features, crs=4326)


def join_attribute(centroids, layer_gdf, source_field, output_column):
    if source_field not in layer_gdf.columns:
        raise KeyError(
            f"Expected field {source_field!r} not found in layer columns: "
            f"{list(layer_gdf.columns)} — schema may have changed."
        )

    joined = geopandas.sjoin(
        centroids[["source_id", "geometry"]],
        layer_gdf[[source_field, "geometry"]],
        how="left",
        predicate="within",
    )
    # A centroid landing exactly on a shared polygon boundary can match
    # more than one feature; keep the first match rather than duplicate
    # the row. Keyed on source_id (the true unique row id), not
    # parcel_id — see module docstring.
    joined = joined.drop_duplicates(subset="source_id", keep="first")
    joined = joined.rename(columns={source_field: output_column})
    return joined.set_index("source_id")[output_column]


def report_unmatched(result, columns):
    total = len(result)
    print(f"\nUnmatched parcels per attribute (of {total:,} total):")
    for col in columns:
        n_unmatched = result[col].isna().sum()
        pct = n_unmatched / total * 100
        print(f"  {col}: {n_unmatched:,} unmatched ({pct:.1f}%)")


def main():
    print(f"Loading parcels from {INPUT_PATH}...")
    centroids = load_parcel_centroids(INPUT_PATH)
    print(f"  {len(centroids):,} parcel centroids computed")

    centroids = flag_out_of_region(centroids, BOP_BBOX_COORDS)

    attributes = {}

    for layer_id, (field, column) in SMAP_LAYERS.items():
        print(f"\nFetching S-map layer {layer_id} ({column})...")
        layer_gdf = fetch_layer_gdf(LRIS_WFS_BASE, layer_id, BOP_BBOX)
        print(f"  {len(layer_gdf):,} polygons fetched")
        attributes[column] = join_attribute(centroids, layer_gdf, field, column)

    print(f"\nFetching LCDB layer {LCDB_LAYER_ID} ({LCDB_COLUMN})...")
    lcdb_gdf = fetch_layer_gdf(LRIS_WFS_BASE, LCDB_LAYER_ID, BOP_BBOX)
    print(f"  {len(lcdb_gdf):,} polygons fetched")
    attributes[LCDB_COLUMN] = join_attribute(centroids, lcdb_gdf, LCDB_FIELD, LCDB_COLUMN)

    result = pd.DataFrame(
        {"source_id": centroids["source_id"], "parcel_id": centroids["parcel_id"]}
    ).set_index("source_id")
    for column, series in attributes.items():
        result[column] = series
    result = result.reset_index()

    report_unmatched(result, attributes.keys())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(OUTPUT_DB) as conn:
        result.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
        conn.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{TABLE_NAME}_source_id "
            f"ON {TABLE_NAME}(source_id)"
        )

    print(f"\nSaved {len(result):,} rows to table '{TABLE_NAME}' in {OUTPUT_DB}")

    assert OUTPUT_DB.exists(), f"Expected output db {OUTPUT_DB} not found — check path"


if __name__ == "__main__":
    main()
