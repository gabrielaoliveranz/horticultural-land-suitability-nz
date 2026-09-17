# =============================================================================
# TERROIR — Unit tests for ingest_parcel_groups.py
# Script: tests/test_ingest_parcel_groups.py
# Stage:  Testing
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Covers the pure grouping functions in src/ingest_parcel_groups.py using
small in-memory fixtures (shapely geometries, plain DataFrames) only —
no terroir.db or parcels_linz.geojson read, so these run on a clean
clone with no data present.
"""

import pandas as pd
from shapely.geometry import Point, Polygon

from ingest_parcel_groups import (
    NON_LAND_SOURCES,
    assign_parcel_groups,
    geometry_key,
)

SQUARE_A = Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])
SQUARE_A_SAME_COORDS = Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])
SQUARE_B = Polygon([(5, 5), (5, 6), (6, 6), (6, 5)])


def test_geometry_key_matches_for_identical_coordinates() -> None:
    assert geometry_key(SQUARE_A) == geometry_key(SQUARE_A_SAME_COORDS)


def test_geometry_key_differs_for_different_coordinates() -> None:
    assert geometry_key(SQUARE_A) != geometry_key(SQUARE_B)


def test_geometry_key_differs_by_geometry_type_too() -> None:
    # A Point at the same location as one of SQUARE_A's vertices must
    # not collide with the polygon's own key.
    assert geometry_key(Point(0, 0)) != geometry_key(SQUARE_A)


def test_assign_parcel_groups_collapses_shared_geometry_to_one_group() -> (
    None
):
    info = pd.DataFrame({
        "source_id": ["t1", "t2", "t3", "t4"],
        "source_category": [
            "NZ Unit of Property", "NZ Unit of Property",
            "NZ Unit of Property", "NZ Property Titles",
        ],
        "is_land_parcel": [True, True, True, True],
        "geometry": [SQUARE_A, SQUARE_A_SAME_COORDS, SQUARE_B, SQUARE_B],
    })

    result = assign_parcel_groups(info)

    # t1 and t2 share SQUARE_A's geometry -> same group, title_count 2.
    assert result.loc[0, "parcel_group_id"] == result.loc[1, "parcel_group_id"]
    assert result.loc[0, "title_count"] == 2
    assert result.loc[1, "title_count"] == 2

    # t3 and t4 share SQUARE_B's geometry -> a different group, title_count 2.
    assert result.loc[2, "parcel_group_id"] == result.loc[3, "parcel_group_id"]
    assert result.loc[2, "title_count"] == 2

    # The two groups are distinct from each other.
    assert result.loc[0, "parcel_group_id"] != result.loc[2, "parcel_group_id"]


def test_assign_parcel_groups_singleton_gets_title_count_one() -> None:
    info = pd.DataFrame({
        "source_id": ["p1"],
        "source_category": ["NZ Primary Parcels"],
        "is_land_parcel": [True],
        "geometry": [SQUARE_A],
    })

    result = assign_parcel_groups(info)

    assert result.loc[0, "title_count"] == 1
    assert result.loc[0, "parcel_group_id"] is not None


def test_assign_parcel_groups_non_land_rows_get_null_group_and_zero() -> (
    None
):
    info = pd.DataFrame({
        "source_id": ["r1"],
        "source_category": ["NZ Primary Parcels - Road"],
        "is_land_parcel": [False],
        "geometry": [SQUARE_A],
    })

    result = assign_parcel_groups(info)

    assert result.loc[0, "parcel_group_id"] is None
    assert result.loc[0, "title_count"] == 0


def test_non_land_sources_are_road_and_hydro_only() -> None:
    # Regression guard: confirmed against a live sample of
    # parcels_linz.geojson — see module docstring for the source
    # values actually seen (NZ Primary Parcels, NZ Primary Parcels -
    # Road, NZ Primary Parcels - Hydro, NZ Property Titles, NZ Unit of
    # Property).
    assert NON_LAND_SOURCES == {
        "NZ Primary Parcels - Road",
        "NZ Primary Parcels - Hydro",
    }
