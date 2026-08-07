# =============================================================================
# TERROIR — Subzone suitability summary
# Script: subzone_summary.py
# Stage:  Scoring
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Joins parcel_scores (source_id, suitability_score) with parcel_attributes's
subzone column on source_id, filters to the 5 named Apophenia subzones
(subzone IS NOT NULL), and computes per subzone: parcel count, mean score,
and the % of parcels in each suitability level (Excellent/Good/Marginal,
per docs/methodology.md, "Score distribution and suitability levels").

The join is inner on source_id against parcel_scores, so parcels excluded
from scoring (null soil attribute) are excluded here too — the subzone
parcel counts reported are therefore slightly below the raw subzone
counts from ingest_subzones.py (2,345+1,027+396+271+78 = 4,117
in-region parcels, minus null-soil exclusions).

Saves the result as a new table `subzone_summary` in
data/processed/terroir.db and prints it as a table.
"""

import pandas as pd

from config import DB_PATH, get_connection

SCORES_TABLE = "parcel_scores"
ATTRIBUTES_TABLE = "parcel_attributes"
SUMMARY_TABLE = "subzone_summary"

# Per docs/methodology.md, "Score distribution and suitability levels".
LEVEL_BINS = [-float("inf"), 5.0, 8.0, float("inf")]
LEVEL_LABELS = ["Marginal", "Good", "Excellent"]


def load_scored_subzones(db_path):
    with get_connection(db_path) as conn:
        scores = pd.read_sql(f"SELECT source_id, suitability_score FROM {SCORES_TABLE}", conn)
        attributes = pd.read_sql(f"SELECT source_id, subzone FROM {ATTRIBUTES_TABLE}", conn)

    joined = scores.merge(attributes, on="source_id", how="inner")
    return joined[joined["subzone"].notna()].copy()


def summarise(subzoned):
    # right=False so bin edges are left-inclusive ([5.0, 8.0), [8.0, inf))
    # matching the documented spec exactly ("Excellent: 8.0-10.0", "Good:
    # 5.0-7.9") — pandas' right=True default put scores of exactly 5.0 or
    # 8.0 in the lower tier, silently misclassifying every parcel that
    # scored precisely on a boundary.
    subzoned["suitability_level"] = pd.cut(
        subzoned["suitability_score"], bins=LEVEL_BINS, labels=LEVEL_LABELS, right=False,
    )

    level_pct = (
        subzoned.groupby("subzone")["suitability_level"]
        .value_counts(normalize=True)
        .unstack(fill_value=0.0) * 100
    )
    level_pct = level_pct.reindex(columns=LEVEL_LABELS, fill_value=0.0)

    summary = subzoned.groupby("subzone").agg(
        parcel_count=("source_id", "count"),
        mean_score=("suitability_score", "mean"),
    )
    summary = summary.join(level_pct.add_suffix("_pct"))
    summary["mean_score"] = summary["mean_score"].round(2)
    for label in LEVEL_LABELS:
        summary[f"{label}_pct"] = summary[f"{label}_pct"].round(1)

    return summary.reset_index().sort_values("parcel_count", ascending=False)


def print_summary(summary):
    columns = ["subzone", "parcel_count", "mean_score", "Excellent_pct", "Good_pct", "Marginal_pct"]
    headers = ["Subzone", "Parcels", "Mean score", "% Excellent", "% Good", "% Marginal"]
    widths = [12, 9, 12, 13, 9, 11]

    def fmt_row(values):
        return "  ".join(str(v).ljust(w) for v, w in zip(values, widths))

    print()
    print(fmt_row(headers))
    print("  ".join("-" * w for w in widths))
    for _, row in summary.iterrows():
        print(fmt_row([row[c] for c in columns]))
    print()


def main():
    print(f"Loading {SCORES_TABLE} + {ATTRIBUTES_TABLE}.subzone from {DB_PATH}...")
    subzoned = load_scored_subzones(DB_PATH)
    print(
        f"  {len(subzoned):,} scored parcels fall within one of the 5 "
        f"named subzones (subzone IS NOT NULL)"
    )

    summary = summarise(subzoned)
    print_summary(summary)

    with get_connection(DB_PATH) as conn:
        summary.to_sql(SUMMARY_TABLE, conn, if_exists="replace", index=False)
        conn.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{SUMMARY_TABLE}_subzone "
            f"ON {SUMMARY_TABLE}(subzone)"
        )

    print(f"Saved {len(summary)} rows to table '{SUMMARY_TABLE}' in {DB_PATH}")

    assert DB_PATH.exists(), f"Expected output db {DB_PATH} not found — check path"


if __name__ == "__main__":
    main()
