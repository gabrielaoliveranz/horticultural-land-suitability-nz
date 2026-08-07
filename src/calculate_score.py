# =============================================================================
# TERROIR — Suitability score calculation
# Script: calculate_score.py
# Stage:  Scoring
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Loads parcel_attributes from data/processed/terroir.db, excludes parcels
with any null soil attribute (per docs/methodology.md, "Handling unmatched
parcels (nulls)" — excluded, not imputed), maps soil_order/soil_texture/
soil_drainage/soil_depth to points per the tables in docs/methodology.md
("Point tables"), and computes:

    suitability_score = (soil_order_pts   * 0.4)
                       + (soil_texture_pts * 0.4)
                       + (soil_drainage_pts * 0.1)
                       + (soil_depth_pts    * 0.1)

Table choice: results are saved to a NEW table, `parcel_scores`, keyed on
source_id — not a column bolted onto parcel_attributes. Reasons: keeps
raw joined data separate from derived/computed scores (mirrors the
project's existing raw/processed folder separation); avoids ambiguity
between "null because excluded from scoring" and "null because not yet
joined"; and makes the table trivial to rebuild (DROP/replace) if the
weights in docs/methodology.md are revised later, without touching
parcel_attributes at all.

Point/category values are mapped from a fixed dict, not a database
lookup — if a soil value appears in the data with no matching entry in
the point table, this fails loudly (KeyError-style ValueError) rather
than silently defaulting to 0, which would understate that parcel's
score without any visible trace.
"""

import sqlite3
from pathlib import Path

import pandas as pd

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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "processed" / "terroir.db"
SOURCE_TABLE = "parcel_attributes"
SCORE_TABLE = "parcel_scores"


def load_parcel_attributes(db_path, table_name):
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql(f"SELECT * FROM {table_name}", conn)


def exclude_unscoreable(df, soil_columns):
    null_mask = df[list(soil_columns)].isna().any(axis=1)
    excluded = df.loc[null_mask]
    scoreable = df.loc[~null_mask].copy()
    return scoreable, excluded


def map_points(series, points_table, column_name):
    unmapped = set(series.unique()) - set(points_table.keys())
    if unmapped:
        raise ValueError(
            f"Unmapped {column_name} value(s): {sorted(unmapped)} — add "
            f"to the point table in docs/methodology.md and this script "
            f"before scoring. Refusing to default to 0."
        )
    return series.map(points_table)


def compute_scores(scoreable):
    for column in SOIL_COLUMNS:
        scoreable[f"{column}_pts"] = map_points(
            scoreable[column], POINT_TABLES[column], column
        )

    scoreable["suitability_score"] = sum(
        scoreable[f"{column}_pts"] * WEIGHTS[column] for column in SOIL_COLUMNS
    ).round(2)

    return scoreable


def report_distribution(scored):
    s = scored["suitability_score"]
    print(f"\nScore distribution ({len(scored):,} scored parcels):")
    print(f"  min:    {s.min():.2f}")
    print(f"  max:    {s.max():.2f}")
    print(f"  mean:   {s.mean():.2f}")
    print(f"  median: {s.median():.2f}")


def report_extremes(scored, n=5):
    cols = ["source_id", "parcel_id", "subzone", "suitability_score"]

    print(f"\nTop {n} parcels by suitability_score:")
    print(scored.nlargest(n, "suitability_score")[cols].to_string(index=False))

    print(f"\nBottom {n} parcels by suitability_score:")
    print(scored.nsmallest(n, "suitability_score")[cols].to_string(index=False))


def main():
    print(f"Loading {SOURCE_TABLE} from {DB_PATH}...")
    df = load_parcel_attributes(DB_PATH, SOURCE_TABLE)
    print(f"  {len(df):,} rows loaded")

    scoreable, excluded = exclude_unscoreable(df, SOIL_COLUMNS)
    print(
        f"\nExcluded {len(excluded):,} of {len(df):,} parcels "
        f"({len(excluded) / len(df) * 100:.1f}%) with a null soil attribute "
        f"— not scored, per docs/methodology.md's null-handling rule."
    )

    scored = compute_scores(scoreable)

    report_distribution(scored)
    report_extremes(scored)

    result_columns = [
        "source_id", "parcel_id", "subzone",
        "soil_order", "soil_order_pts",
        "soil_texture", "soil_texture_pts",
        "soil_drainage", "soil_drainage_pts",
        "soil_depth", "soil_depth_pts",
        "suitability_score",
    ]
    result = scored[result_columns]

    with sqlite3.connect(DB_PATH) as conn:
        result.to_sql(SCORE_TABLE, conn, if_exists="replace", index=False)
        conn.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{SCORE_TABLE}_source_id "
            f"ON {SCORE_TABLE}(source_id)"
        )

    print(f"\nSaved {len(result):,} rows to table '{SCORE_TABLE}' in {DB_PATH}")

    assert DB_PATH.exists(), f"Expected output db {DB_PATH} not found — check path"


if __name__ == "__main__":
    main()
