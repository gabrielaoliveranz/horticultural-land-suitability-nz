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
118,265 parcels — mostly urban/residential and unusable for this analysis.
Filtered to parcels > 10,000 m² (1 ha), reducing to 17,400 parcels:
Western Bay of Plenty District 11,028, Tauranga City 3,237, Ōpōtiki
District 3,135. This threshold is a size-based proxy, not a true
land-use filter (LINZ has no land-use field); it may include some
non-horticultural rural land.

(Earlier figures of 109,513 / 14,265 covered only 2 of the 3 TAs — a
macron mismatch in the CQL filter silently excluded all of Opotiki
District from the first Fase 2 run through several iterations. Fixed by
filtering on `territorial_authority_ascii`; see docs/data_sources.md,
"Technical note (macrons)".)

LCDB v6.0 (LRIS layer 123148) provides real land-use classification,
including an "Orchard, Vineyard or Other Perennial Crop" class — 1,809
polygons (3.0%) of 60,368 total in the Bay of Plenty bbox. LCDB's own
1 ha minimum mapping unit independently aligns with the area threshold
above.

(Earlier figures of 1,411 / 7.2% of 19,525 were based on the same
narrower, pre-fix bbox as above — re-run with the corrected filter and
widened bbox in src/00_explore_volumes.py.)

Decision: LCDB class is joined to each parcel via spatial join (centroid-
in-polygon) as an **attribute**, not used to filter parcels out. Filtering
by LCDB class would eliminate the ability to answer business question 2
(zones with no current horticultural use that could be considered for
expansion) — a parcel with good soil/area but no current orchard use is
exactly the candidate that question needs to surface, not discard.

---

## Scoring model

The full scoring model (weightings and reasoning) is defined in Fase 3.
The following rule is fixed now, ahead of that, because it depends on
ingestion results already in hand rather than on scoring weights.

### Handling unmatched parcels (nulls)

953 of 17,400 parcels (5.5%) have no S-map match (soil_depth, soil_texture,
soil_drainage, soil_order all null); 57 (0.3%) have no LCDB match. These
parcels fall outside S-map's/LCDB's mapped coverage — typically coastal
edge cases, not a data quality error (see docs/data_sources.md ingestion
notes). The unmatched rate rose from 0.8% to 5.5% once Opotiki District's
3,135 parcels were correctly included — plausible given Opotiki's more
remote/coastal terrain (East Cape localities, offshore islands) likely
has thinner S-map coverage than the Tauranga/Western Bay urban-fringe
area the 0.8% figure was based on.

Decision: parcels with any null soil attribute are excluded from the
suitability score entirely, not assigned a default/imputed value.
Inventing a soil value for a parcel with no real data would undermine the
credibility of the score for every parcel, not just the affected ones.
These excluded parcels are reported separately (count + list) rather than
silently dropped, so the case study can state coverage honestly.
