# =============================================================================
# TERROIR — Power BI export (summary CSVs)
# Script: export_powerbi_summaries.py
# Stage:  Export
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Rebuilds every summary CSV in data/powerbi_export/ from the current
terroir.db, replacing what were previously manual, unversioned exports
(nothing in the repo produced them before this script, which is how
they carried the pre parcel-grouping-fix numbers with no code anyone
could re-run to refresh them — see ingest_parcel_groups.py and
calculate_score.py for that fix, and docs/methodology.md's
"Physical-parcel grouping" section for the full before/after):

  - suitability_levels_summary.csv: straight export of the
    suitability_levels_summary table.
  - subzone_summary.csv: straight export of the subzone_summary table.
  - expansion_candidates.csv: the expansion_candidates table, joined to
    parcels_linz.geojson for territorial_authority (not stored in the
    table itself, source_id is the join key — see
    regional_summary_expansion.py's docstring).
  - territorial_authority_summary.csv: NEW aggregation, not previously
    backed by any script. Mirrors subzone_summary.py's summarise()
    logic exactly (same LEVEL_BINS/LEVEL_LABELS, same right=False
    boundary fix) but grouped by territorial_authority instead of
    subzone, covering every scored parcel (all 4 TAs), not just the 5
    named Apophenia subzones.
  - parcel_scores_for_map_SAMPLE500.csv: first 500 rows of the current
    parcel_scores_for_map.csv, same convention as the existing sample
    file (a lighter-weight file for quick Power BI iteration).

subzone_climate_risk.csv is deliberately NOT touched here: it's built
from the average centroid of every parcel_attributes row assigned a
given subzone (ingest_subzones.py runs before ingest_parcel_groups.py
even exists, and assigns subzone to every raw feature regardless of
is_land_parcel or title duplication), so it's unaffected by the
road/hydro exclusion or the multi-title collapse — nothing to
refresh there.
"""

import logging
from pathlib import Path

import geopandas
import pandas as pd

from config import DATA_DIR, DB_PATH, PARCELS_PATH, configure_logging
from config import get_connection

logger = logging.getLogger(__name__)

EXPORT_DIR = DATA_DIR / "powerbi_export"

LEVEL_BINS = [-float("inf"), 5.0, 8.0, float("inf")]
LEVEL_LABELS = ["Marginal", "Good", "Excellent"]

SAMPLE_SIZE = 500


def load_geo_lookup(path: Path) -> pd.DataFrame:
    parcels = geopandas.read_file(path)
    return pd.DataFrame({
        "source_id": parcels["source_id"],
        "territorial_authority": parcels["territorial_authority"],
    })


def export_table_as_is(db_path: Path, table_name: str, out_path: Path) -> None:
    with get_connection(db_path) as conn:
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    logger.info(f"Saved {len(df):,} rows to {out_path}")


def export_expansion_candidates(
    db_path: Path, geo_lookup: pd.DataFrame, out_path: Path
) -> None:
    with get_connection(db_path) as conn:
        candidates = pd.read_sql("SELECT * FROM expansion_candidates", conn)
    result = candidates.merge(geo_lookup, on="source_id", how="left")
    result.to_csv(out_path, index=False, encoding="utf-8-sig")
    logger.info(f"Saved {len(result):,} rows to {out_path}")


def summarise_by(df: pd.DataFrame, group_column: str) -> pd.DataFrame:
    """Same logic as subzone_summary.py's summarise(), generalised to
    group by an arbitrary column (here, territorial_authority)."""
    df = df.copy()
    df["suitability_level"] = pd.cut(
        df["suitability_score"], bins=LEVEL_BINS, labels=LEVEL_LABELS,
        right=False,
    )

    level_pct = (
        df.groupby(group_column)["suitability_level"]
        .value_counts(normalize=True)
        .unstack(fill_value=0.0) * 100
    )
    level_pct = level_pct.reindex(columns=LEVEL_LABELS, fill_value=0.0)

    summary = df.groupby(group_column).agg(
        parcel_count=("source_id", "count"),
        mean_score=("suitability_score", "mean"),
    )
    summary = summary.join(level_pct.add_suffix("_pct"))
    summary["mean_score"] = summary["mean_score"].round(2)
    for label in LEVEL_LABELS:
        summary[f"{label}_pct"] = summary[f"{label}_pct"].round(1)

    return summary.reset_index().sort_values(
        "parcel_count", ascending=False
    )


def export_territorial_authority_summary(
    db_path: Path, geo_lookup: pd.DataFrame, out_path: Path
) -> None:
    with get_connection(db_path) as conn:
        scores = pd.read_sql(
            "SELECT source_id, suitability_score FROM parcel_scores", conn
        )
    scored_with_ta = scores.merge(geo_lookup, on="source_id", how="left")
    summary = summarise_by(scored_with_ta, "territorial_authority")
    summary.to_csv(out_path, index=False, encoding="utf-8-sig")
    logger.info(f"Saved {len(summary):,} rows to {out_path}")


def export_sample(source_csv: Path, out_path: Path, n: int) -> None:
    df = pd.read_csv(source_csv).head(n)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    logger.info(f"Saved {len(df):,} rows to {out_path}")


def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    export_table_as_is(
        DB_PATH, "suitability_levels_summary",
        EXPORT_DIR / "suitability_levels_summary.csv",
    )
    export_table_as_is(
        DB_PATH, "subzone_summary", EXPORT_DIR / "subzone_summary.csv",
    )

    logger.info(f"Loading territorial_authority lookup from {PARCELS_PATH}...")
    geo_lookup = load_geo_lookup(PARCELS_PATH)

    export_expansion_candidates(
        DB_PATH, geo_lookup, EXPORT_DIR / "expansion_candidates.csv",
    )
    export_territorial_authority_summary(
        DB_PATH, geo_lookup,
        EXPORT_DIR / "territorial_authority_summary.csv",
    )
    export_sample(
        EXPORT_DIR / "parcel_scores_for_map.csv",
        EXPORT_DIR / "parcel_scores_SAMPLE500.csv",
        SAMPLE_SIZE,
    )


if __name__ == "__main__":
    configure_logging()
    main()
