# =============================================================================
# TERROIR — Unit tests for regional_summary_expansion.py
# Script: tests/test_regional_summary_expansion.py
# Stage:  Testing
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Regression coverage for the suitability-level binning boundary bug
documented in docs/methodology.md, "Score distribution and suitability
levels": pandas.cut's default right=True is right-inclusive, which
misclassified scores of exactly 5.0 and 8.0 into the lower tier. Bins are
left-inclusive ([5.0, 8.0), [8.0, inf)) via right=False, so 5.0 must land
in "Good" and 8.0 must land in "Excellent" — not "Marginal" / "Good".

Uses small in-memory DataFrame fixtures only — no terroir.db read, so
these run on a clean clone with no data present.
"""

import pandas as pd

from regional_summary_expansion import compute_levels_summary


def test_boundary_scores_are_left_inclusive() -> None:
    scores = pd.DataFrame({"suitability_score": [5.0, 8.0]})

    summary = compute_levels_summary(scores)
    counts = summary.set_index("suitability_level")["parcel_count"]

    assert counts["Good"] == 1
    assert counts["Excellent"] == 1
    assert counts["Marginal"] == 0


def test_scores_bin_into_expected_levels() -> None:
    scores = pd.DataFrame({
        "suitability_score": [0.0, 4.99, 5.0, 7.99, 8.0, 10.0],
    })

    summary = compute_levels_summary(scores)
    counts = summary.set_index("suitability_level")["parcel_count"]

    assert counts["Marginal"] == 2  # 0.0, 4.99
    assert counts["Good"] == 2      # 5.0, 7.99
    assert counts["Excellent"] == 2  # 8.0, 10.0
