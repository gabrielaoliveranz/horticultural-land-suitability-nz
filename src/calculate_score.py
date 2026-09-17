# =============================================================================
# TERROIR — Suitability score calculation
# Script: calculate_score.py
# Stage:  Scoring
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Loads parcel_attributes from data/processed/terroir.db, excludes rows
that aren't land (is_land_parcel False — roads and hydro features that
ingest_linz.py's CQL_FILTER doesn't screen out, flagged by
ingest_parcel_groups.py) and rows with any null soil attribute (per
docs/methodology.md, "Handling unmatched parcels (nulls)" — excluded,
not imputed), maps soil_order/soil_texture/soil_drainage/soil_depth to
points per the tables in docs/methodology.md ("Point tables"), and
computes:

    suitability_score = (soil_order_pts   * 0.4)
                       + (soil_texture_pts * 0.4)
                       + (soil_drainage_pts * 0.1)
                       + (soil_depth_pts    * 0.1)

Multi-title collapse: rows sharing a parcel_group_id (assigned by
ingest_parcel_groups.py) are the same physical parcel recorded under
more than one legal title — cross leases, unit titles, life estates,
and title-correction records that coincide with their underlying
parcel's boundary rather than describing separate land (see that
script's docstring for how this was confirmed). Because every row in a
group is joined off the identical geometry, they always carry identical
soil attributes and score identically, so collapsing to one row per
parcel_group_id loses no scoring information — dedupe_by_parcel_group()
does this last, after scoring, and keeps title_count on the surviving
row so the fact that a parcel carries several titles isn't lost, just
no longer double-counted as separate parcels.

Table choice: results are saved to a NEW table, `parcel_scores`, keyed
on source_id — not a column bolted onto parcel_attributes. Reasons:
keeps raw joined data separate from derived/computed scores (mirrors
the project's existing raw/processed folder separation); avoids
ambiguity between "null because excluded from scoring" and "null
because not yet joined"; and makes the table trivial to rebuild
(DROP/replace) if the weights in docs/methodology.md are revised later,
without touching parcel_attributes at all. The same reasoning is why
this script excludes and collapses rows rather than deleting anything
from parcel_attributes — every raw title record stays queryable there.

Point/category values are mapped from a fixed dict, not a database
lookup — if a soil value appears in the data with no matching entry in
the point table, this fails loudly (KeyError-style ValueError) rather
than silently defaulting to 0, which would understate that parcel's
score without any visible trace.
"""

import logging
from pathlib import Path
from typing import Iterable

import pandas as pd

from config import DB_PATH, configure_logging, get_connection

logger = logging.getLogger(__name__)

SOIL_ORDER_POINTS = {
    "Allophanic": 10,
    "Pumice": 10,
    "Brown": 6,
    "Recent": 6,
    "Anthropic": 5,
    "Raw": 4,
    "Podzol": 3,
    "Gley": 2,
    "Organic": 1,
}
SOIL_TEXTURE_POINTS = {
    "Loamy": 10,
    "Silty": 7,
    "Sandy": 5,
    "Clayey": 2,
    "Peaty": 1,
}
SOIL_DRAINAGE_POINTS = {
    "Well drained": 10,
    "Moderately well drained": 8,
    "Imperfectly drained": 5,
    "Poorly drained": 2,
    "Very poorly drained": 0,
}
SOIL_DEPTH_POINTS = {
    "Deep": 10,
    "Moderately Deep": 6,
    "Shallow": 3,
    "Very Shallow": 1,
}

WEIGHTS = {
    "soil_order": 0.4,
    "soil_texture": 0.4,
    "soil_drainage": 0.1,
    "soil_depth": 0.1,
}

SOIL_COLUMNS = ("soil_order", "soil_texture", "soil_drainage", "soil_depth")
POINT_TABLES = {
    "soil_order": SOIL_ORDER_POINTS,
    "soil_texture": SOIL_TEXTURE_POINTS,
    "soil_drainage": SOIL_DRAINAGE_POINTS,
    "soil_depth": SOIL_DEPTH_POINTS,
}

SOURCE_TABLE = "parcel_attributes"
SCORE_TABLE = "parcel_scores"


def load_parcel_attributes(db_path: Path, table_name: str) -> pd.DataFrame:
    with get_connection(db_path) as conn:
        return pd.read_sql(f"SELECT * FROM {table_name}", conn)


def exclude_non_land(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Splits off rows flagged is_land_parcel=False by
    ingest_parcel_groups.py (roads, hydro) — these were never meant to
    be scored for horticultural suitability at all."""
    land_mask = df["is_land_parcel"].astype(bool)
    land = df.loc[land_mask].copy()
    non_land = df.loc[~land_mask]
    return land, non_land


def exclude_unscoreable(
    df: pd.DataFrame, soil_columns: Iterable[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    null_mask = df[list(soil_columns)].isna().any(axis=1)
    excluded = df.loc[null_mask]
    scoreable = df.loc[~null_mask].copy()
    return scoreable, excluded


def map_points(
    series: pd.Series, points_table: dict, column_name: str
) -> pd.Series:
    unmapped = set(series.unique()) - set(points_table.keys())
    if unmapped:
        raise ValueError(
            f"Unmapped {column_name} value(s): {sorted(unmapped)} — add "
            f"to the point table in docs/methodology.md and this script "
            f"before scoring. Refusing to default to 0."
        )
    return series.map(points_table)


def compute_scores(scoreable: pd.DataFrame) -> pd.DataFrame:
    for column in SOIL_COLUMNS:
        scoreable[f"{column}_pts"] = map_points(
            scoreable[column], POINT_TABLES[column], column
        )

    scoreable["suitability_score"] = sum(
        scoreable[f"{column}_pts"] * WEIGHTS[column]
        for column in SOIL_COLUMNS
    ).round(2)

    return scoreable


def dedupe_by_parcel_group(df: pd.DataFrame) -> pd.DataFrame:
    """Collapses rows that share a parcel_group_id (the same physical
    parcel recorded under more than one legal title — see module
    docstring) into a single row, keeping title_count so the fact
    isn't lost. Deterministic: keeps the row with the lexicographically
    smallest source_id in each group, so re-running produces the same
    survivor every time."""
    return (
        df.sort_values("source_id")
        .drop_duplicates(subset="parcel_group_id", keep="first")
        .reset_index(drop=True)
    )


def report_distribution(scored: pd.DataFrame) -> None:
    s = scored["suitability_score"]
    logger.info(f"Score distribution ({len(scored):,} scored parcels):")
    logger.info(f"  min:    {s.min():.2f}")
    logger.info(f"  max:    {s.max():.2f}")
    logger.info(f"  mean:   {s.mean():.2f}")
    logger.info(f"  median: {s.median():.2f}")


def report_extremes(scored: pd.DataFrame, n: int = 5) -> None:
    cols = ["source_id", "parcel_id", "subzone", "suitability_score"]

    logger.info(f"Top {n} parcels by suitability_score:")
    logger.info(
        scored.nlargest(n, "suitability_score")[cols].to_string(index=False)
    )

    logger.info(f"Bottom {n} parcels by suitability_score:")
    logger.info(
        scored.nsmallest(n, "suitability_score")[cols].to_string(index=False)
    )


def main() -> None:
    logger.info(f"Loading {SOURCE_TABLE} from {DB_PATH}...")
    df = load_parcel_attributes(DB_PATH, SOURCE_TABLE)
    logger.info(f"  {len(df):,} rows loaded")

    land, non_land = exclude_non_land(df)
    logger.warning(
        f"Excluded {len(non_land):,} of {len(df):,} rows "
        f"({len(non_land) / len(df) * 100:.1f}%) flagged as road or "
        f"hydro, not land — see ingest_parcel_groups.py."
    )

    scoreable, excluded = exclude_unscoreable(land, SOIL_COLUMNS)
    logger.warning(
        f"Excluded {len(excluded):,} of {len(land):,} land parcels "
        f"({len(excluded) / len(land) * 100:.1f}%) with a null soil "
        f"attribute — not scored, per docs/methodology.md's "
        f"null-handling rule."
    )

    scored = compute_scores(scoreable)

    deduped = dedupe_by_parcel_group(scored)
    n_collapsed = len(scored) - len(deduped)
    logger.warning(
        f"Collapsed {len(scored):,} scored rows into {len(deduped):,} "
        f"distinct physical parcels ({n_collapsed:,} rows were extra "
        f"legal-title records on already-counted land, see "
        f"ingest_parcel_groups.py) — title_count on each surviving row "
        f"records how many titles it represents."
    )

    report_distribution(deduped)
    report_extremes(deduped)

    result_columns = [
        "source_id", "parcel_id", "subzone",
        "soil_order", "soil_order_pts",
        "soil_texture", "soil_texture_pts",
        "soil_drainage", "soil_drainage_pts",
        "soil_depth", "soil_depth_pts",
        "suitability_score", "title_count",
    ]
    result = deduped[result_columns]

    with get_connection(DB_PATH) as conn:
        result.to_sql(SCORE_TABLE, conn, if_exists="replace", index=False)
        conn.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{SCORE_TABLE}_source_id "
            f"ON {SCORE_TABLE}(source_id)"
        )

    logger.info(
        f"Saved {len(result):,} rows to table '{SCORE_TABLE}' in {DB_PATH}"
    )

    assert DB_PATH.exists(), (
        f"Expected output db {DB_PATH} not found — check path"
    )


if __name__ == "__main__":
    configure_logging()
    main()
