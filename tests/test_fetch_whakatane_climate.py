# =============================================================================
# TERROIR — Unit tests for fetch_whakatane_climate.py
# Script: tests/test_fetch_whakatane_climate.py
# Stage:  Testing
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Covers append_whakatane_row(), the one pure/testable piece of
fetch_whakatane_climate.py — everything else in that script makes a
live Open-Meteo API call, consistent with how ingest_climate_risk.py
and ingest_linz.py are also left untested here (see those scripts'
own docstrings and CLAUDE.md's testing convention). Uses pytest's
tmp_path fixture only — no terroir.db or parcels_linz.geojson read.
"""

import csv

from fetch_whakatane_climate import FIELDNAMES, append_whakatane_row

SAMPLE_ROW = {
    "subzone": "Whakatane District",
    "lat": -38.077226,
    "lon": 176.869339,
    "frost_days": 100,
    "frost_days_per_year": 10.0,
    "chill_hours_annual_avg": 1068.1,
    "heavy_rain_days": 203,
    "heavy_rain_days_per_year": 20.3,
}


def test_append_whakatane_row_writes_header_on_new_file(tmp_path) -> None:
    out_csv = tmp_path / "subzone_climate_risk.csv"

    append_whakatane_row(out_csv, SAMPLE_ROW)

    with open(out_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 1
    assert rows[0]["subzone"] == "Whakatane District"
    assert rows[0]["frost_days"] == "100"


def test_append_whakatane_row_does_not_repeat_header(tmp_path) -> None:
    out_csv = tmp_path / "subzone_climate_risk.csv"
    out_csv.write_text(",".join(FIELDNAMES) + "\n", encoding="utf-8")

    append_whakatane_row(out_csv, SAMPLE_ROW)

    with open(out_csv, newline="", encoding="utf-8") as f:
        lines = f.readlines()

    # Exactly one header line, followed by exactly one data row.
    assert lines[0].strip() == ",".join(FIELDNAMES)
    assert len(lines) == 2


def test_append_whakatane_row_appends_without_overwriting(tmp_path) -> None:
    out_csv = tmp_path / "subzone_climate_risk.csv"

    append_whakatane_row(out_csv, SAMPLE_ROW)
    other_row = {**SAMPLE_ROW, "subzone": "Some Other Row"}
    append_whakatane_row(out_csv, other_row)

    with open(out_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2
    assert [r["subzone"] for r in rows] == [
        "Whakatane District", "Some Other Row",
    ]
