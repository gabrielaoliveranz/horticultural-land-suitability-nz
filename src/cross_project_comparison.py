# =============================================================================
# TERROIR — Cross-project comparison with Apophenia (business question 3)
# Script: cross_project_comparison.py
# Stage:  Scoring
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Answers business question 3: does high operational risk (Apophenia)
correlate with low soil suitability (Terroir), or is the risk primarily
logistical rather than agronomic?

Loads subzone_summary (Terroir's real soil-derived mean_score per
subzone) from data/processed/terroir.db, loads
data/external/dim_corridor_apophenia.csv (Apophenia's corridor risk
data), and joins on subzone (exact string match — both projects use
plain "Opotiki"/"Tauranga"/etc., already confirmed compatible; no
locality-name macron handling needed here since this is a small,
manually-authored 5-row lookup, not a WFS response).

Computes Pearson correlation between Terroir's mean_score and each of
Apophenia's 3 risk indicators (distance_port_km, base_risk_weight,
psa_incidence_historical), across only 5 subzones — a directional
signal, not a statistically powered result. See docs/methodology.md,
"Cross-project comparison (business question 3)" for the real-vs-
synthetic caveat that governs how this result may be used.

Saves the joined comparison table as `cross_project_comparison` in
terroir.db and prints the table plus the correlation values.
"""

import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "processed" / "terroir.db"
CORRIDOR_CSV_PATH = PROJECT_ROOT / "data" / "external" / "dim_corridor_apophenia.csv"
SUMMARY_TABLE = "subzone_summary"
COMPARISON_TABLE = "cross_project_comparison"

RISK_INDICATORS = ("distance_port_km", "base_risk_weight", "psa_incidence_historical")


def load_terroir_summary(db_path):
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql(f"SELECT subzone, mean_score FROM {SUMMARY_TABLE}", conn)


def load_apophenia_corridors(csv_path):
    return pd.read_csv(csv_path)


def build_comparison(terroir, apophenia):
    columns = ["subzone", "mean_score", *RISK_INDICATORS]
    comparison = terroir.merge(apophenia, on="subzone", how="inner")[columns]
    return comparison.sort_values("mean_score", ascending=False).reset_index(drop=True)


def compute_correlations(comparison):
    return {
        indicator: comparison["mean_score"].corr(comparison[indicator])
        for indicator in RISK_INDICATORS
    }


def print_comparison(comparison):
    columns = ["subzone", "mean_score", *RISK_INDICATORS]
    headers = ["Subzone", "Mean score", "Dist. port (km)", "Base risk wt", "PSA incidence"]
    widths = [12, 12, 16, 13, 14]

    def fmt_row(values):
        return "  ".join(str(v).ljust(w) for v, w in zip(values, widths))

    print()
    print(fmt_row(headers))
    print("  ".join("-" * w for w in widths))
    for _, row in comparison.iterrows():
        print(fmt_row([row[c] for c in columns]))
    print()


def print_correlations(correlations):
    print("Pearson correlation: Terroir mean_score vs. each Apophenia risk indicator")
    print("(n=5 subzones — directional signal only, not statistically powered)")
    for indicator, r in correlations.items():
        print(f"  {indicator}: r = {r:.3f}")
    print()


def main():
    print(f"Loading {SUMMARY_TABLE} from {DB_PATH}...")
    terroir = load_terroir_summary(DB_PATH)
    print(f"  {len(terroir)} subzones loaded")

    print(f"Loading Apophenia corridor data from {CORRIDOR_CSV_PATH}...")
    apophenia = load_apophenia_corridors(CORRIDOR_CSV_PATH)
    print(f"  {len(apophenia)} corridors loaded")

    comparison = build_comparison(terroir, apophenia)
    if len(comparison) != len(terroir):
        raise ValueError(
            f"Join on subzone dropped rows: {len(terroir)} Terroir subzones "
            f"in, {len(comparison)} out — check subzone spelling agreement "
            f"between subzone_summary and {CORRIDOR_CSV_PATH.name}."
        )

    print_comparison(comparison)

    correlations = compute_correlations(comparison)
    print_correlations(correlations)

    with sqlite3.connect(DB_PATH) as conn:
        comparison.to_sql(COMPARISON_TABLE, conn, if_exists="replace", index=False)
        conn.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{COMPARISON_TABLE}_subzone "
            f"ON {COMPARISON_TABLE}(subzone)"
        )

    print(f"Saved {len(comparison)} rows to table '{COMPARISON_TABLE}' in {DB_PATH}")

    assert DB_PATH.exists(), f"Expected output db {DB_PATH} not found — check path"


if __name__ == "__main__":
    main()
