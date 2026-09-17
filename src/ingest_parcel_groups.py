# =============================================================================
# TERROIR — Physical-parcel grouping (multi-title / road-hydro flagging)
# Script: ingest_parcel_groups.py
# Stage:  Ingestion
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Loads data/processed/parcels_linz.geojson and adds four columns to the
existing `parcel_attributes` table in data/processed/terroir.db via an
SQL UPDATE keyed on source_id — same pattern as ingest_subzones.py, the
table is not rebuilt:

  - source_category: the LINZ `source` property as-is (e.g. "NZ Primary
    Parcels", "NZ Unit of Property"), kept as a plain reference column,
    same spirit as parcel_id — see ingest_soil_lcdb.py's docstring.
  - is_land_parcel: False for the two non-land categories
    ("NZ Primary Parcels - Road", "NZ Primary Parcels - Hydro") that
    ingest_linz.py's CQL_FILTER does not exclude (it only filters on
    territorial_authority and area, so roads and water bodies over the
    1ha threshold pass straight through). True for everything else.
  - parcel_group_id / title_count: rows that share the exact same
    boundary geometry are the same physical piece of land recorded
    under more than one legal property/title record — cross leases,
    unit titles (blocks of units), life estates, and "Supplementary
    Record Sheet" correction records all coincide with their underlying
    parcel's boundary rather than describing separate land. Confirmed
    empirically against the live file: of 22,834 raw features, only
    rows whose source is "NZ Unit of Property" or "NZ Property Titles"
    ever share a geometry with another row — "NZ Primary Parcels" and
    its Road/Hydro variants never do, and no duplicate-geometry group
    is 100% identical across every column (only the location-derived
    ones), which rules out a simple re-fetched-the-same-row bug.
    Every row sharing a geometry gets the same parcel_group_id and the
    group's row count as title_count, so downstream reporting
    (calculate_score.py) can collapse them into one row per physical
    parcel without losing the fact that several titles exist over it.

Exact-match grouping (no distance tolerance) is safe here because
ingest_linz.py already snaps every geometry to a fixed 1e-6 degree grid
(PRECISION_GRID_DEG, ~11cm) before saving parcels_linz.geojson — two
rows on the same physical land land on byte-identical coordinates, they
don't merely land close together.

Data-integrity bug, not a coverage gap (per CLAUDE.md's "stop and ask
before modifying already-committed files" rule): the source/road-hydro
mix-up and the multi-title duplication were both confirmed with Gaby,
in chat, before this script was written.

ingest_linz.py's own CQL_FILTER is deliberately left unchanged here —
whether LINZ's WFS even supports filtering on `source` server-side is
unconfirmed, and CLAUDE.md's "never hardcode field names or category
codes without confirming against a live sample" cuts against guessing
at that syntax. Flagging is_land_parcel downstream, against the
already-fetched local file, needed no live call to verify.
"""

import hashlib
import logging
from pathlib import Path

import geopandas
import pandas as pd

from config import DB_PATH, PARCELS_PATH, configure_logging, get_connection

logger = logging.getLogger(__name__)

TABLE_NAME = "parcel_attributes"

# Confirmed against a live sample of parcels_linz.geojson (22,834
# features) — see module docstring.
NON_LAND_SOURCES = frozenset({
    "NZ Primary Parcels - Road",
    "NZ Primary Parcels - Hydro",
})


def load_parcel_source_info(path: Path) -> pd.DataFrame:
    parcels = geopandas.read_file(path)
    return pd.DataFrame({
        "source_id": parcels["source_id"],
        "source_category": parcels["source"],
        "is_land_parcel": ~parcels["source"].isin(NON_LAND_SOURCES),
        "geometry": parcels.geometry,
    })


def geometry_key(geometry) -> str:
    """Stable hash of a geometry's exact coordinates. Safe as an exact
    (not fuzzy) "same physical footprint" test only because
    ingest_linz.py snaps every geometry to a fixed precision grid
    before saving — see module docstring."""
    return hashlib.sha1(geometry.wkb).hexdigest()


def assign_parcel_groups(info: pd.DataFrame) -> pd.DataFrame:
    """Adds parcel_group_id / title_count for land rows only. Non-land
    rows (is_land_parcel False) get a null group and a title_count of
    0 — they're excluded from suitability analysis entirely in
    calculate_score.py, so grouping them would be meaningless."""
    result = info.drop(columns="geometry").copy()
    result["parcel_group_id"] = pd.Series(
        [None] * len(result), dtype="object"
    )
    result["title_count"] = 0

    land_mask = info["is_land_parcel"]
    land_geom_keys = info.loc[land_mask, "geometry"].apply(geometry_key)
    result.loc[land_mask, "parcel_group_id"] = land_geom_keys
    result.loc[land_mask, "title_count"] = (
        land_geom_keys.groupby(land_geom_keys).transform("count")
    )

    return result


def report_groups(result: pd.DataFrame) -> None:
    total = len(result)
    n_non_land = int((~result["is_land_parcel"]).sum())
    logger.warning(
        f"{n_non_land:,} of {total:,} raw features are roads or "
        f"hydro, not land — flagged is_land_parcel=False, to be "
        f"excluded from scoring in calculate_score.py."
    )

    land = result.loc[result["is_land_parcel"]]
    dupe_titles = land.loc[land["title_count"] > 1, "parcel_group_id"]
    n_groups = dupe_titles.nunique()
    n_rows = len(dupe_titles)
    logger.warning(
        f"{n_groups:,} physical parcel(s) carry more than one legal "
        f"title record, totalling {n_rows:,} rows ({n_rows - n_groups:,} "
        f"rows in excess of one-per-parcel) — these collapse to one "
        f"row per parcel in parcel_scores, with title_count preserved."
    )


def update_parcel_group_columns(
    db_path: Path, table_name: str, result: pd.DataFrame
) -> None:
    with get_connection(db_path) as conn:
        existing_cols = [
            row[1]
            for row in conn.execute(f"PRAGMA table_info({table_name})")
        ]
        for column, sql_type in (
            ("source_category", "TEXT"),
            ("is_land_parcel", "INTEGER"),
            ("parcel_group_id", "TEXT"),
            ("title_count", "INTEGER"),
        ):
            if column not in existing_cols:
                conn.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {column} "
                    f"{sql_type}"
                )

        result.to_sql(
            "parcel_group_lookup", conn, if_exists="replace", index=False
        )
        conn.execute(
            f"""
            UPDATE {table_name}
            SET source_category = (
                    SELECT source_category FROM parcel_group_lookup
                    WHERE parcel_group_lookup.source_id
                        = {table_name}.source_id
                ),
                is_land_parcel = (
                    SELECT is_land_parcel FROM parcel_group_lookup
                    WHERE parcel_group_lookup.source_id
                        = {table_name}.source_id
                ),
                parcel_group_id = (
                    SELECT parcel_group_id FROM parcel_group_lookup
                    WHERE parcel_group_lookup.source_id
                        = {table_name}.source_id
                ),
                title_count = (
                    SELECT title_count FROM parcel_group_lookup
                    WHERE parcel_group_lookup.source_id
                        = {table_name}.source_id
                )
            """
        )
        conn.execute("DROP TABLE parcel_group_lookup")
        conn.commit()


def main() -> None:
    logger.info(f"Loading parcel source info from {PARCELS_PATH}...")
    info = load_parcel_source_info(PARCELS_PATH)
    logger.info(f"  {len(info):,} raw features loaded")

    result = assign_parcel_groups(info)
    report_groups(result)

    update_parcel_group_columns(DB_PATH, TABLE_NAME, result)
    logger.info(
        f"Updated source_category/is_land_parcel/parcel_group_id/"
        f"title_count columns on table '{TABLE_NAME}' in {DB_PATH}"
    )

    assert DB_PATH.exists(), (
        f"Expected output db {DB_PATH} not found — check path"
    )


if __name__ == "__main__":
    configure_logging()
    main()
