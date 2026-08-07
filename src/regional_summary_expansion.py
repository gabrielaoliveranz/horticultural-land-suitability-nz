# =============================================================================
# TERROIR — Regional suitability summary and expansion candidates
# Script: regional_summary_expansion.py
# Stage:  Scoring
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Answers business question 1 (region-wide, not just the 5 named subzones —
subzone_summary.py already covers those) and business question 2
(expansion candidates).

Part 1 — business question 1 (full regional picture):
Groups every scored parcel in parcel_scores into suitability levels
(Excellent 8.0-10.0, Good 5.0-7.9, Marginal <5.0, same bins as
subzone_summary.py — both use right=False so a score of exactly 5.0
or 8.0 lands in the higher tier, matching this range notation exactly)
and reports count + % per level across the whole dataset, not just
parcels within Apophenia's 5 named subzones. Saved as
`suitability_levels_summary`.

Part 2 — business question 2 (expansion candidates):
Joins parcel_scores with parcel_attributes (lcdb_class_2023, subzone) on
source_id, then filters to suitability_score >= 8.0 (Excellent tier —
same boundary as Part 1's binning, kept consistent so a parcel counted
Excellent in one table is never absent from the other) AND
lcdb_class_2023 != 'Orchard, Vineyard or Other Perennial Crop' — parcels
with good-to-excellent soil that aren't already growing orchard/vineyard/
perennial crops, i.e. real expansion candidates rather than existing
orchards. Parcels with a NULL lcdb_class_2023 (no LCDB match) pass this
filter too, since NULL is not equal to the orchard string either — they're
not confirmed non-orchard, but they're not confirmed orchard, and
excluding them would silently drop otherwise-qualifying parcels just
because LCDB has a coverage gap there. Saved as `expansion_candidates`
(source_id, suitability_score, lcdb_class_2023, subzone) — source_id is
the join key back to parcels_linz.geojson for mapping geometry later, no
geometry is duplicated into this table.

Both parts save into data/processed/terroir.db and print their summary.
"""

import logging
from pathlib import Path

import pandas as pd

from config import DB_PATH, configure_logging, get_connection

logger = logging.getLogger(__name__)

SCORES_TABLE = "parcel_scores"
ATTRIBUTES_TABLE = "parcel_attributes"
LEVELS_SUMMARY_TABLE = "suitability_levels_summary"
EXPANSION_TABLE = "expansion_candidates"

# Per docs/methodology.md, "Score distribution and suitability levels" —
# same bins as subzone_summary.py.
LEVEL_BINS = [-float("inf"), 5.0, 8.0, float("inf")]
LEVEL_LABELS = ["Marginal", "Good", "Excellent"]

EXCELLENT_THRESHOLD = 8.0
ORCHARD_CLASS = "Orchard, Vineyard or Other Perennial Crop"
OUTSIDE_SUBZONES_LABEL = "Outside the 5 named subzones"


def load_scores(db_path: Path) -> pd.DataFrame:
    with get_connection(db_path) as conn:
        return pd.read_sql(
            f"SELECT source_id, suitability_score FROM {SCORES_TABLE}", conn
        )


def load_attributes(db_path: Path) -> pd.DataFrame:
    with get_connection(db_path) as conn:
        return pd.read_sql(
            f"SELECT source_id, lcdb_class_2023, subzone "
            f"FROM {ATTRIBUTES_TABLE}",
            conn,
        )


def compute_levels_summary(scores: pd.DataFrame) -> pd.DataFrame:
    # right=False: see subzone_summary.py's summarise() for why — matches
    # the documented "Excellent: 8.0-10.0" / "Good: 5.0-7.9" spec exactly,
    # and keeps this consistent with compute_expansion_candidates() below,
    # which filters on the same >= 8.0 boundary.
    levels = pd.cut(
        scores["suitability_score"],
        bins=LEVEL_BINS, labels=LEVEL_LABELS, right=False,
    )
    counts = levels.value_counts().reindex(LEVEL_LABELS)
    total = len(scores)

    summary = pd.DataFrame({
        "suitability_level": LEVEL_LABELS,
        "parcel_count": counts.values,
    })
    summary["pct"] = (summary["parcel_count"] / total * 100).round(1)
    return summary


def print_levels_summary(summary: pd.DataFrame, total: int) -> None:
    headers = ["Level", "Parcels", "% of total"]
    widths = [12, 10, 12]

    def fmt_row(values: list) -> str:
        return "  ".join(str(v).ljust(w) for v, w in zip(values, widths))

    logger.info(f"Suitability levels, region-wide ({total:,} scored parcels):")
    logger.info(fmt_row(headers))
    logger.info("  ".join("-" * w for w in widths))
    for _, row in summary.iterrows():
        logger.info(fmt_row([
            row["suitability_level"],
            f"{row['parcel_count']:,}",
            f"{row['pct']}%",
        ]))
    logger.info("")


def compute_expansion_candidates(
    scores: pd.DataFrame, attributes: pd.DataFrame
) -> pd.DataFrame:
    merged = scores.merge(attributes, on="source_id", how="inner")
    is_excellent = merged["suitability_score"] >= EXCELLENT_THRESHOLD
    is_not_orchard = merged["lcdb_class_2023"] != ORCHARD_CLASS
    return merged.loc[is_excellent & is_not_orchard, [
        "source_id", "suitability_score", "lcdb_class_2023", "subzone",
    ]].reset_index(drop=True)


def print_expansion_summary(candidates: pd.DataFrame) -> None:
    logger.info(
        f"Expansion candidates (suitability_score >= "
        f"{EXCELLENT_THRESHOLD}, not already {ORCHARD_CLASS!r}): "
        f"{len(candidates):,} parcels"
    )

    breakdown = (
        candidates["subzone"].fillna(OUTSIDE_SUBZONES_LABEL).value_counts()
    )

    headers = ["Subzone", "Parcels"]
    widths = [30, 10]

    def fmt_row(values: list) -> str:
        return "  ".join(str(v).ljust(w) for v, w in zip(values, widths))

    logger.info("")
    logger.info(fmt_row(headers))
    logger.info("  ".join("-" * w for w in widths))
    for subzone, count in breakdown.items():
        logger.info(fmt_row([subzone, f"{count:,}"]))
    logger.info("")


def save_table(
    db_path: Path, table_name: str, df: pd.DataFrame, key_column: str
) -> None:
    with get_connection(db_path) as conn:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{key_column} "
            f"ON {table_name}({key_column})"
        )
    logger.info(f"Saved {len(df):,} rows to table '{table_name}' in {db_path}")


def main() -> None:
    logger.info(f"Loading {SCORES_TABLE} from {DB_PATH}...")
    scores = load_scores(DB_PATH)
    logger.info(f"  {len(scores):,} scored parcels loaded")

    # Part 1 — business question 1, region-wide.
    levels_summary = compute_levels_summary(scores)
    print_levels_summary(levels_summary, len(scores))
    save_table(
        DB_PATH, LEVELS_SUMMARY_TABLE, levels_summary, "suitability_level"
    )

    # Part 2 — business question 2, expansion candidates.
    logger.info(f"Loading {ATTRIBUTES_TABLE} (lcdb_class_2023, subzone)...")
    attributes = load_attributes(DB_PATH)

    candidates = compute_expansion_candidates(scores, attributes)
    print_expansion_summary(candidates)
    save_table(DB_PATH, EXPANSION_TABLE, candidates, "source_id")

    assert DB_PATH.exists(), (
        f"Expected output db {DB_PATH} not found — check path"
    )


if __name__ == "__main__":
    configure_logging()
    main()
