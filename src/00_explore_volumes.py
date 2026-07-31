# =============================================================================
# TERROIR — Exploratory volume/complexity check for LINZ and S-map layers
# Script: 00_explore_volumes.py
# Stage:  Ingestion (pre-Fase 2 exploration)
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
One-off exploration script. NOT the ingestion pipeline.

Queries LINZ layer 122657 (NZ Property Boundaries, filtered to the three
territorial authorities) and the four confirmed S-map layers (filtered to a
Bay of Plenty bounding box, since S-map has no territorial_authority field),
then prints feature counts and average vertices-per-polygon.

Also tests area thresholds (5,000 / 10,000 / 20,000 / 40,000 m²) on the
LINZ layer, within the same 3-TA filter, to gauge parcel counts remaining
at each cutoff.

Also queries LCDB (LRIS layer 123148) within the Bay of Plenty bbox: first
confirms the real 2023/24 land-cover field name and the exact "orchard"
class string/code from a live sample (never assumed), then reports total
LCDB polygons in the bbox vs. how many fall in that class.

Purpose: gauge real data volume and geometry complexity before locking the
SQLite vs SpatiaLite storage decision, and pick a defensible minimum-area
cutoff for ingestion based on the actual distribution. No database writes
here.
"""

import os
import re
from statistics import mean

import requests
from dotenv import load_dotenv

load_dotenv()

LINZ_API_KEY = os.environ["LINZ_API_KEY"]
LRIS_API_KEY = os.environ["LRIS_API_KEY"]

LINZ_WFS_BASE = f"https://data.linz.govt.nz/services;key={LINZ_API_KEY}/wfs"
LRIS_WFS_BASE = f"https://lris.scinfo.org.nz/services;key={LRIS_API_KEY}/wfs"

# Sample size used to estimate average vertices/polygon — full totals are
# read from the WFS response's totalFeatures field, not from this sample.
SAMPLE_SIZE = 500
REQUEST_TIMEOUT = 120

TERRITORIAL_AUTHORITIES = (
    "Tauranga City",
    "Western Bay of Plenty District",
    "Opotiki District",
)
LINZ_CQL_FILTER = "territorial_authority IN ({})".format(
    ", ".join(f"'{ta}'" for ta in TERRITORIAL_AUTHORITIES)
)

# Bay of Plenty bounding box (Katikati to Opotiki): min_lon, min_lat,
# max_lon, max_lat, CRS84 (lon/lat order).
BOP_BBOX_COORDS = (175.7, -38.2, 177.4, -37.2)
BOP_BBOX = "{},{},{},{},urn:ogc:def:crs:OGC:1.3:CRS84".format(*BOP_BBOX_COORDS)

# Layer 122657 carries a server-computed "area" property in m² — no need
# to reproject geometry client-side to test these cutoffs.
AREA_THRESHOLDS_M2 = (5_000, 10_000, 20_000, 40_000)

SMAP_LAYERS = {
    122758: "S-map Soil Depth",
    122760: "S-map Soil Texture",
    122764: "S-map Soil Drainage",
    122765: "S-map Soil Classification",
}

LCDB_LAYER_ID = 123148
LCDB_GEOMETRY_FIELD = "GEOMETRY"  # confirmed via DescribeFeatureType


def bbox_cql(field_name, coords=BOP_BBOX_COORDS):
    # This WFS rejects requests that set both `bbox` and `cql_filter` (500:
    # "bbox and cql_filter both specified but are mutually exclusive"), so
    # any query that needs an attribute filter alongside the bbox has to
    # fold the bbox into the CQL itself via BBOX(). The CRS must be spelled
    # out explicitly — BBOX() without one silently matches nothing here.
    min_lon, min_lat, max_lon, max_lat = coords
    return (
        f"BBOX({field_name}, {min_lon}, {min_lat}, {max_lon}, {max_lat}, "
        f"'urn:ogc:def:crs:OGC:1.3:CRS84')"
    )


def wfs_get(base_url, layer_id, *, count=None, cql_filter=None, bbox=None):
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": f"layer-{layer_id}",
        "outputFormat": "json",
    }
    if count:
        params["count"] = count
    if cql_filter:
        params["cql_filter"] = cql_filter
    if bbox:
        params["bbox"] = bbox

    response = requests.get(base_url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def wfs_hits(base_url, layer_id, *, cql_filter=None, bbox=None):
    # resultType=hits ignores outputFormat=json on this WFS (Koordinates/
    # GeoServer) and always answers with an XML FeatureCollection whose
    # root element carries the total match count as numberMatched.
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": f"layer-{layer_id}",
        "resultType": "hits",
    }
    if cql_filter:
        params["cql_filter"] = cql_filter
    if bbox:
        params["bbox"] = bbox

    response = requests.get(base_url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    match = re.search(r'numberMatched="(\d+)"', response.text)
    if not match:
        raise ValueError(f"numberMatched not found in hits response: {response.text[:300]}")
    return int(match.group(1))


def count_vertices(geometry):
    if geometry is None:
        return 0
    gtype = geometry["type"]
    coords = geometry["coordinates"]
    if gtype == "Polygon":
        return sum(len(ring) for ring in coords)
    if gtype == "MultiPolygon":
        return sum(len(ring) for polygon in coords for ring in polygon)
    return 0


def query_layer(base_url, layer_id, label, *, cql_filter=None, bbox=None):
    print(f"Querying {label} (layer {layer_id})...")

    sample = wfs_get(
        base_url, layer_id,
        count=SAMPLE_SIZE, cql_filter=cql_filter, bbox=bbox,
    )
    features = sample.get("features", [])

    total = sample.get("totalFeatures")
    if not isinstance(total, int):
        total = wfs_hits(base_url, layer_id, cql_filter=cql_filter, bbox=bbox)

    vertex_counts = [
        count_vertices(f.get("geometry"))
        for f in features
        if f.get("geometry")
    ]
    avg_vertices = mean(vertex_counts) if vertex_counts else 0.0

    return {
        "layer": label,
        "layer_id": layer_id,
        "total_features": total,
        "sample_size": len(features),
        "avg_vertices_per_polygon": round(avg_vertices, 1),
    }


def print_summary(rows):
    headers = ("Layer", "ID", "Total features", "Sample", "Avg vertices/poly")
    widths = (32, 8, 16, 8, 20)

    def fmt_row(values):
        return "  ".join(str(v).ljust(w) for v, w in zip(values, widths))

    print()
    print(fmt_row(headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(fmt_row((
            row["layer"],
            row["layer_id"],
            row["total_features"],
            row["sample_size"],
            row["avg_vertices_per_polygon"],
        )))
    print()


def query_area_thresholds(base_url, layer_id, base_cql_filter, thresholds):
    rows = []
    for threshold in thresholds:
        cql_filter = f"({base_cql_filter}) AND area > {threshold}"
        print(f"Querying area > {threshold:,} m2 ...")
        parcels = wfs_hits(base_url, layer_id, cql_filter=cql_filter)
        rows.append({"threshold_m2": threshold, "parcels": parcels})
    return rows


def print_area_thresholds(rows, baseline):
    headers = ("Area threshold", "Parcels remaining", "% of original")
    widths = (18, 20, 16)

    def fmt_row(values):
        return "  ".join(str(v).ljust(w) for v, w in zip(values, widths))

    print()
    print(f"Baseline (3-TA filter, no area cutoff): {baseline:,} parcels")
    print()
    print(fmt_row(headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        pct = row["parcels"] / baseline * 100
        print(fmt_row((
            f"> {row['threshold_m2']:,} m2",
            f"{row['parcels']:,}",
            f"{pct:.1f}%",
        )))
    print()


def confirm_lcdb_orchard_field(base_url, layer_id, bbox_filter_cql):
    # LCDB field names carry a survey-year suffix that changes release to
    # release (Name_2023/Class_2023 here), and the exact class string/code
    # isn't documented anywhere we've read — both are confirmed live from
    # a real matching feature rather than assumed.
    print("Confirming LCDB 2023/24 orchard field name and class value...")
    sample = wfs_get(
        base_url, layer_id, count=1,
        cql_filter=f"{bbox_filter_cql} AND Name_2023 LIKE '%Orchard%'",
    )
    features = sample.get("features", [])
    if not features:
        raise RuntimeError(
            "No LCDB feature matched Name_2023 LIKE '%Orchard%' in the bbox — "
            "field name or class string may have changed, check schema manually."
        )
    props = features[0]["properties"]
    name_value = props["Name_2023"]
    class_value = props["Class_2023"]
    print(f"  Confirmed: Name_2023 = {name_value!r}, Class_2023 = {class_value}")
    return name_value, class_value


def query_lcdb_orchard(base_url, layer_id):
    bbox_filter_cql = bbox_cql(LCDB_GEOMETRY_FIELD)
    name_value, class_value = confirm_lcdb_orchard_field(base_url, layer_id, bbox_filter_cql)

    print(f"Querying LCDB (layer {layer_id}) totals in bbox...")
    total = wfs_hits(base_url, layer_id, cql_filter=bbox_filter_cql)

    orchard_by_class = wfs_hits(
        base_url, layer_id,
        cql_filter=f"{bbox_filter_cql} AND Class_2023 = {class_value}",
    )
    orchard_by_name = wfs_hits(
        base_url, layer_id,
        cql_filter=f"{bbox_filter_cql} AND Name_2023 = '{name_value}'",
    )
    if orchard_by_class != orchard_by_name:
        raise RuntimeError(
            f"Class_2023={class_value} count ({orchard_by_class}) disagrees with "
            f"Name_2023={name_value!r} count ({orchard_by_name}) — "
            "code/name mapping may not be 1:1, investigate before trusting either."
        )

    return {
        "class_name": name_value,
        "class_code": class_value,
        "total_polygons": total,
        "orchard_polygons": orchard_by_class,
    }


def print_lcdb_summary(result):
    pct = result["orchard_polygons"] / result["total_polygons"] * 100
    print()
    print(f"LCDB 2023/24 class checked: {result['class_name']!r} (Class_2023 = {result['class_code']})")
    print()
    headers = ("Total LCDB polygons (bbox)", "Orchard/Vineyard/Perennial", "% of total")
    widths = (28, 28, 12)

    def fmt_row(values):
        return "  ".join(str(v).ljust(w) for v, w in zip(values, widths))

    print(fmt_row(headers))
    print("  ".join("-" * w for w in widths))
    print(fmt_row((
        f"{result['total_polygons']:,}",
        f"{result['orchard_polygons']:,}",
        f"{pct:.1f}%",
    )))
    print()


def main():
    results = []

    linz_result = query_layer(
        LINZ_WFS_BASE, 122657, "NZ Property Boundaries",
        cql_filter=LINZ_CQL_FILTER,
    )
    results.append(linz_result)

    for layer_id, label in SMAP_LAYERS.items():
        results.append(query_layer(
            LRIS_WFS_BASE, layer_id, label,
            bbox=BOP_BBOX,
        ))

    print_summary(results)

    area_rows = query_area_thresholds(
        LINZ_WFS_BASE, 122657, LINZ_CQL_FILTER, AREA_THRESHOLDS_M2,
    )
    print_area_thresholds(area_rows, linz_result["total_features"])

    lcdb_result = query_lcdb_orchard(LRIS_WFS_BASE, LCDB_LAYER_ID)
    print_lcdb_summary(lcdb_result)


if __name__ == "__main__":
    main()
