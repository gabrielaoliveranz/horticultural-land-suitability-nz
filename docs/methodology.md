# Methodology

Documents the modelling and tooling decisions behind Terroir, and the
reasoning behind each one, as they are made.

---

## Dashboard tool: Streamlit

**Decision:** Streamlit, not Power BI.

**Locked in:** Fase 0, per `docs/conventions.md` — not to be revisited
once Fase 2 (data ingestion) begins.

**Reasoning:**

- Demonstrates an end-to-end Python skillset — data ingestion,
  geospatial processing, modelling, and presentation all in one
  language — rather than splitting the toolchain between Python and a
  separate BI tool.
- Better fit for the GIS/geospatial analyst roles this portfolio
  targets (e.g. Tauranga City Council, Western Bay of Plenty District
  Council), where Python and open-source geospatial libraries (such as
  geopandas) are more directly relevant than Power BI authoring.
- Keeps the whole project version-controllable as plain text in one
  repository, rather than a binary `.pbix` file that doesn't diff
  cleanly in git — this also supports the "same-commit doc update"
  discipline in `docs/conventions.md`, since changes to a Streamlit app
  show up as an ordinary git diff.
- Apophenia already demonstrates a Python-first, interactive build;
  Streamlit continues that stack story rather than introducing an
  unrelated BI tool purely for the sake of contrast.

**Trade-off acknowledged:** Power BI remains more common in many
corporate and council BI teams day to day, so this choice favours
breadth of Python skill over BI-tool-specific familiarity. Noted here
so the decision isn't second-guessed later without a documented reason.

---

## Waterlogging risk: drainage-only proxy (DEM excluded)

LINZ elevation data (DEM) was evaluated for a flood/waterlogging risk
proxy and deliberately excluded. Reasoning: elevation alone is not a
reliable flood indicator without flow direction and catchment analysis,
which is out of scope. S-map soil drainage class already encodes
waterlogging likelihood directly, making it a more relevant proxy with
no added technical complexity (DEM requires raster handling — rasterio/
STAC — a different toolchain from the vector WFS sources already in use).
Elevation is noted as a possible v2 extension, not a current gap.

---

## Parcel selection: area threshold + LCDB as attribute, not filter

LINZ Property Boundaries (layer 122657) within the 3 target TAs returns
109,513 parcels — mostly urban/residential and unusable for this analysis.
Filtered to parcels > 10,000 m² (1 ha), reducing to 14,265 parcels. This
threshold is a size-based proxy, not a true land-use filter (LINZ has no
land-use field); it may include some non-horticultural rural land.

LCDB v6.0 (LRIS layer 123148) provides real land-use classification,
including an "Orchard, Vineyard or Other Perennial Crop" class — 1,411
polygons (7.2%) in the Bay of Plenty bbox. LCDB's own 1 ha minimum mapping
unit independently aligns with the area threshold above.

Decision: LCDB class is joined to each parcel via spatial join (centroid-
in-polygon) as an **attribute**, not used to filter parcels out. Filtering
by LCDB class would eliminate the ability to answer business question 2
(zones with no current horticultural use that could be considered for
expansion) — a parcel with good soil/area but no current orchard use is
exactly the candidate that question needs to surface, not discard.

---

## Scoring model

To be populated in Fase 3, once weightings and reasoning are defined.
