# =============================================================================
# TERROIR — Unit tests for calculate_score.py
# Script: tests/test_calculate_score.py
# Stage:  Testing
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Covers the pure scoring functions in src/calculate_score.py using small
in-memory DataFrame fixtures only — no terroir.db read, so these run on a
clean clone with no data present.
"""

import pandas as pd
import pytest

from calculate_score import (
    SOIL_COLUMNS,
    SOIL_DEPTH_POINTS,
    SOIL_DRAINAGE_POINTS,
    SOIL_ORDER_POINTS,
    SOIL_TEXTURE_POINTS,
    compute_scores,
    exclude_unscoreable,
    map_points,
)


def test_map_points_raises_on_unmapped_category():
    series = pd.Series(["Allophanic", "NotACategory"])
    with pytest.raises(ValueError, match="NotACategory"):
        map_points(series, SOIL_ORDER_POINTS, "soil_order")


def test_map_points_maps_known_categories():
    series = pd.Series(["Allophanic", "Brown"])
    result = map_points(series, SOIL_ORDER_POINTS, "soil_order")
    assert result.tolist() == [10, 6]


def test_exclude_unscoreable_partitions_without_losing_rows():
    df = pd.DataFrame({
        "source_id": [1, 2, 3, 4],
        "soil_order": ["Allophanic", None, "Brown", "Recent"],
        "soil_texture": ["Loamy", "Sandy", "Sandy", None],
        "soil_drainage": ["Well drained", "Imperfectly drained", "Imperfectly drained", "Poorly drained"],
        "soil_depth": ["Deep", "Shallow", "Shallow", "Shallow"],
    })

    scoreable, excluded = exclude_unscoreable(df, SOIL_COLUMNS)

    # Rows 1 (index 0) and 3 (index 2) have no nulls in any soil column.
    assert sorted(scoreable["source_id"].tolist()) == [1, 3]
    # Rows 2 and 4 each have a null in at least one soil column.
    assert sorted(excluded["source_id"].tolist()) == [2, 4]
    # No rows lost or duplicated across the two partitions.
    assert len(scoreable) + len(excluded) == len(df)


def test_exclude_unscoreable_keeps_all_rows_when_none_are_null():
    df = pd.DataFrame({
        "source_id": [1, 2],
        "soil_order": ["Allophanic", "Brown"],
        "soil_texture": ["Loamy", "Sandy"],
        "soil_drainage": ["Well drained", "Imperfectly drained"],
        "soil_depth": ["Deep", "Shallow"],
    })

    scoreable, excluded = exclude_unscoreable(df, SOIL_COLUMNS)

    assert len(scoreable) == 2
    assert len(excluded) == 0


def test_compute_scores_matches_hand_calculated_weighted_result():
    # soil_order=Brown(6), soil_texture=Sandy(5), soil_drainage=Imperfectly
    # drained(5), soil_depth=Shallow(3).
    # score = 6*0.4 + 5*0.4 + 5*0.1 + 3*0.1 = 2.4 + 2.0 + 0.5 + 0.3 = 5.2
    assert SOIL_ORDER_POINTS["Brown"] == 6
    assert SOIL_TEXTURE_POINTS["Sandy"] == 5
    assert SOIL_DRAINAGE_POINTS["Imperfectly drained"] == 5
    assert SOIL_DEPTH_POINTS["Shallow"] == 3

    df = pd.DataFrame({
        "soil_order": ["Brown"],
        "soil_texture": ["Sandy"],
        "soil_drainage": ["Imperfectly drained"],
        "soil_depth": ["Shallow"],
    })

    result = compute_scores(df)

    assert result.loc[0, "suitability_score"] == pytest.approx(5.2)
