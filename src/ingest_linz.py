# =============================================================================
# TERROIR — LINZ Property Boundaries ingestion
# Script: ingest_linz.py
# Stage:  Ingestion
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Fetches LINZ layer 122657 (NZ Property Boundaries), filtered server-side
via CQL_FILTER to the 4 target territorial authorities AND area > 10,000 m2
(the 1 ha threshold locked in docs/methodology.md, "Parcel selection: area
threshold + LCDB as attribute, not filter"), and saves the result as
data/processed/parcels_linz.geojson.

Confirmed during Fase 2 exploration: this WFS rejects requests that set
both `bbox` and `cql_filter` (500 "mutually exclusive") — same quirk as
the LRIS WFS documented in docs/data_sources.md. Not an issue here since
this script only needs the attribute filter, no bbox.

Macron bug fix (see docs/data_sources.md, "Technical note (macrons)"):
this layer's `territorial_authority` field uses official macron spelling
("Ōpōtiki District"), not the plain-ASCII "Opotiki District" this script
originally filtered on. That silently matched 0 of 8,752 Opotiki District
parcels since the first Fase 2 run — the "3 target TAs" were actually
only 2. Filtering now uses `territorial_authority_ascii` for all names,
not just Opotiki, since any of them could have the same macron trap.

Scope expansion (see docs/data_sources.md, "Scope completeness
verification"): Whakatane District added as a 4th target TA after
confirming, with real LINZ/LCDB data rather than assumption, that it
contains documented kiwifruit growing land (Edgecumbe / Rangitaiki
Plains) while the region's other 2 excluded TAs (Kawerau District,
Rotorua District) do not — Kawerau has 0.00% orchard/vineyard/perennial-
crop LCDB coverage (checked via real parcel boundaries, not a bbox
approximation) and Rotorua's is negligible (0.25%).

Geometry simplification (moved here from dashboard runtime): the
dashboard's two pydeck map pages (2_Suitability_Map.py,
3_Expansion_Candidates.py) used to call shapely.simplify() and
set_precision() on every cold start — the same ~108MB read + full-
dataset simplify every time Streamlit's cache was empty, dominating
cold-load time regardless of which subzone ended up displayed (see
those pages' own "Performance pass" docstring notes for the measured
numbers this was chasing). Simplifying once here, at ingestion time,
means the canonical parcels_linz.geojson is already at map-ready
precision — every downstream consumer (the dashboard, and 02/03 below)
loads pre-simplified geometry directly, no runtime cost.

Tolerance (SIMPLIFY_TOLERANCE_DEG, 0.00005 deg, ~5m max deviation at
this latitude) and precision grid (PRECISION_GRID_DEG, 1e-6, ~11cm) are
carried over unchanged from the dashboard's own values — already
verified there via the Douglas-Peucker guarantee and Web Mercator
pixel-resolution math (shapely.simplify(preserve_topology=True) bounds
every point to within `tolerance` of the original, not a heuristic).

Downstream risk, checked rather than assumed: ingest_soil_lcdb.py
and ingest_subzones.py both compute a centroid per parcel and
spatial-join it (predicate="within") against soil/LCDB/locality
polygons — a simplification-shifted centroid could in principle cross
a polygon boundary and change a match. Re-ran both against the
resimplified file and diffed every row against the pre-change output:
see docs/methodology.md for the actual comparison (this docstring
states the risk existed and was checked, not the specific numbers,
which would go stale here without a corresponding pipeline re-run).
"""

import os
from pathlib import Path

import geopandas
import requests
import shapely
from dotenv import load_dotenv

load_dotenv()

LINZ_API_KEY = os.environ["LINZ_API_KEY"]
LINZ_WFS_BASE = f"https://data.linz.govt.nz/services;key={LINZ_API_KEY}/wfs"

LAYER_ID = 122657
PAGE_SIZE = 1000
REQUEST_TIMEOUT = 120

TERRITORIAL_AUTHORITIES = (
    "Tauranga City",
    "Western Bay of Plenty District",
    "Opotiki District",
    "Whakatane District",
)
AREA_THRESHOLD_M2 = 10_000

# territorial_authority_ascii, not territorial_authority — see module
# docstring's macron note.
CQL_FILTER = "territorial_authority_ascii IN ({}) AND area > {}".format(
    ", ".join(f"'{ta}'" for ta in TERRITORIAL_AUTHORITIES),
    AREA_THRESHOLD_M2,
)

# Exploration (src/explore_volumes.py) swept area thresholds client-side
# against a 109,513-parcel baseline that, due to the macron bug above, only
# covered Tauranga City + Western Bay of Plenty District. With Opotiki
# District now correctly included, a materially higher row count than the
# old ~14,265 figure is expected, not a bug.
EXPECTED_ROW_COUNT_APPROX = 14_265

# Carried over unchanged from the dashboard's own values — see module
# docstring's "Geometry simplification" note for the derivation.
SIMPLIFY_TOLERANCE_DEG = 0.00005   # ~5m max deviation at this latitude
PRECISION_GRID_DEG = 1e-6          # 6 decimal places, ~11cm

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
OUTPUT_PATH = OUTPUT_DIR / "parcels_linz.geojson"


def fetch_all_features(base_url, layer_id, cql_filter, page_size=PAGE_SIZE):
    features = []
    start_index = 0
    while True:
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": f"layer-{layer_id}",
            "outputFormat": "json",
            "cql_filter": cql_filter,
            "count": page_size,
            "startIndex": start_index,
            # This WFS's native/declared CRS is EPSG:4167 (NZGD2000), not
            # WGS84 — request explicit reprojection so the output is truly
            # EPSG:4326, matching the crs we label the GeoDataFrame with.
            "srsName": "urn:ogc:def:crs:EPSG::4326",
        }
        response = requests.get(base_url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        page_features = response.json().get("features", [])
        features.extend(page_features)
        print(f"  fetched {len(features)} features so far...")

        if len(page_features) < page_size:
            break
        start_index += page_size

    return features


def main():
    print(f"Fetching LINZ layer {LAYER_ID} with filter:\n  {CQL_FILTER}")
    features = fetch_all_features(LINZ_WFS_BASE, LAYER_ID, CQL_FILTER)

    gdf = geopandas.GeoDataFrame.from_features(features, crs="EPSG:4326")

    print(
        f"\nSimplifying geometry (tolerance={SIMPLIFY_TOLERANCE_DEG} deg "
        f"~5m, precision grid={PRECISION_GRID_DEG} ~11cm)..."
    )
    gdf["geometry"] = gdf.geometry.simplify(SIMPLIFY_TOLERANCE_DEG, preserve_topology=True)
    gdf["geometry"] = gdf.geometry.apply(
        lambda g: shapely.set_precision(g, grid_size=PRECISION_GRID_DEG)
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    gdf.to_file(OUTPUT_PATH, driver="GeoJSON")

    print(f"\nSaved {len(gdf)} parcels (pre-simplified) to {OUTPUT_PATH}")
    print(
        f"Prior runs reported approx. {EXPECTED_ROW_COUNT_APPROX:,} parcels — "
        f"that figure only covered 2 of 3 TAs due to the macron bug fixed "
        f"above, so a materially higher count here is correct, not a bug."
    )

    assert OUTPUT_DIR.exists(), f"Expected output dir {OUTPUT_DIR} not found — check path"


if __name__ == "__main__":
    main()
