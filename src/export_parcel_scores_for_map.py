# =============================================================================
# TERROIR — Power BI export (parcel_scores_for_map.csv)
# Script: export_parcel_scores_for_map.py
# Stage:  Export
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Builds data/powerbi_export/parcel_scores_for_map.csv from parcel_scores
(terroir.db) plus per-parcel location fields read straight from
parcels_linz.geojson (territorial_authority, area, and a WGS84 centroid
computed the same way as ingest_soil_lcdb.py's load_parcel_centroids —
projected to NZTM2000 for an accurate centroid, then back to WGS84).

This replaces a manual, unversioned export: nothing in the repo produced
parcel_scores_for_map.csv before this script — it was built by hand once
against an earlier version of parcel_scores, which is how it carried
21,491 rows (pre road/hydro exclusion and pre multi-title collapse) with
no code anyone could re-run to reproduce or update it. See
ingest_parcel_groups.py and calculate_score.py for that fix.

suitability_level is recomputed here with the exact same bins used in
regional_summary_expansion.py / subzone_summary.py (Excellent 8.0-10.0,
Good 5.0-7.9, Marginal <5.0, right=False) rather than read from a table,
since parcel_scores itself doesn't store it.

title_count (from calculate_score.py, sourced from
ingest_parcel_groups.py) is carried straight through as the last column
— how many legal-title records this physical parcel represents.
"""

import logging
from pathlib import Path

import geopandas
import pandas as pd

from config import (
    DATA_DIR,
    DB_PATH,
    PARCELS_PATH,
    configure_logging,
    get_connection,
)

logger = logging.getLogger(__name__)

OUTPUT_PATH = DATA_DIR / "powerbi_export" / "parcel_scores_for_map.csv"

# Same bins as regional_summary_expansion.py / subzone_summary.py — see
# docs/methodology.md, "Score distribution and suitability levels".
LEVEL_BINS = [-float("inf"), 5.0, 8.0, float("inf")]
LEVEL_LABELS = ["Marginal", "Good", "Excellent"]

SCORE_COLUMNS = [
    "source_id", "subzone", "soil_order", "soil_texture", "soil_drainage",
    "soil_depth", "suitability_score", "title_count",
]
COLUMN_ORDER = [
    "source_id", "subzone", "soil_order", "soil_texture", "soil_drainage",
    "soil_depth", "suitability_score", "suitability_level",
    "territorial_authority", "area_m2", "lat", "lon", "title_count",
]


def load_scores(db_path: Path) -> pd.DataFrame:
    with get_connection(db_path) as conn:
        return pd.read_sql(
            f"SELECT {', '.join(SCORE_COLUMNS)} FROM parcel_scores", conn
        )


def load_geo_info(path: Path) -> pd.DataFrame:
    parcels = geopandas.read_file(path)
    # Centroid computed in a projected CRS (NZTM2000) for accuracy, then
    # converted back to WGS84 — same approach as
    # ingest_soil_lcdb.py's load_parcel_centroids.
    centroids = parcels.to_crs(2193).geometry.centroid.to_crs(4326)
    return pd.DataFrame({
        "source_id": parcels["source_id"],
        "territorial_authority": parcels["territorial_authority"],
        "area_m2": parcels["area"],
        "lat": centroids.y,
        "lon": centroids.x,
    })


def build_export(scores: pd.DataFrame, geo_info: pd.DataFrame) -> pd.DataFrame:
    scores = scores.copy()
    scores["suitability_level"] = pd.cut(
        scores["suitability_score"], bins=LEVEL_BINS, labels=LEVEL_LABELS,
        right=False,
    )
    merged = scores.merge(geo_info, on="source_id", how="left")
    return merged[COLUMN_ORDER]


def main() -> None:
    logger.info(f"Loading parcel_scores from {DB_PATH}...")
    scores = load_scores(DB_PATH)
    logger.info(f"  {len(scores):,} scored parcels loaded")

    logger.info(f"Loading location fields from {PARCELS_PATH}...")
    geo_info = load_geo_info(PARCELS_PATH)

    result = build_export(scores, geo_info)

    n_missing_geo = result["lat"].isna().sum()
    if n_missing_geo:
        logger.warning(
            f"{n_missing_geo:,} scored parcels had no matching geometry "
            f"in {PARCELS_PATH} — check source_id alignment."
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    logger.info(f"Saved {len(result):,} rows to {OUTPUT_PATH}")

    assert OUTPUT_PATH.exists(), f"Expected output {OUTPUT_PATH} not found"


if __name__ == "__main__":
    configure_logging()
    main()
