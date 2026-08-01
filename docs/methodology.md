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

LINZ Property Boundaries (layer 122657) within the 4 target TAs returns
139,452 parcels — mostly urban/residential and unusable for this analysis.
Filtered to parcels > 10,000 m² (1 ha), reducing to 22,834 parcels:
Western Bay of Plenty District 11,028, Whakatane District 5,434,
Tauranga City 3,237, Ōpōtiki District 3,135. This threshold is a
size-based proxy, not a true land-use filter (LINZ has no land-use
field); it may include some non-horticultural rural land.

(Earlier figures of 109,513 / 14,265 covered only 2 of the original 3
TAs — a macron mismatch in the CQL filter silently excluded all of
Opotiki District from the first Fase 2 run through several iterations.
Fixed by filtering on `territorial_authority_ascii`; see
docs/data_sources.md, "Technical note (macrons)". A later figure of
17,400/118,265 covered the correct 3 TAs before Whakatane District was
added as a 4th — see "Scope completeness verification" in
docs/data_sources.md for why.)

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

### Point tables

**soil_order** (0-10):
Allophanic 10, Pumice 10, Brown 6, Recent 6, Anthropic 5, Raw 4, Podzol 3, Gley 2, Organic 1

**soil_texture** (0-10):
Loamy 10, Silty 7, Sandy 5, Clayey 2, Peaty 1

**soil_drainage** (0-10):
Well drained 10, Moderately well drained 8, Imperfectly drained 5, Poorly drained 2, Very poorly drained 0

**soil_depth** (0-10):
Deep 10, Moderately Deep 6, Shallow 3, Very Shallow 1

Point values are based on kiwifruit soil requirement research (NZKGI,
Te Ara Encyclopedia, general agronomic sources — see chat history for
citations), not derived from the source data itself.

### Weights

score = (soil_order × 0.4) + (soil_texture × 0.4) + (soil_drainage × 0.1) + (soil_depth × 0.1)

Weight rationale: soil_order and soil_texture show high variation across
the 22,834 parcels (soil_order ranges from 41.7% Allophanic + 28.2%
Pumice down to <1% Anthropic; soil_texture is 64.2% Loamy down to <1%
Clayey), making them meaningful differentiators. soil_drainage and
soil_depth are more skewed (86.5% "Well drained", 94.1% "Deep"),
providing less differentiating signal across most parcels — though with
Whakatane District added, both are noticeably less dominant than the
original 3-TA figures (>90% / >96% respectively), since Whakatane's
soil profile is more varied than Tauranga/Western Bay/Opotiki's.

**Important caveat:** the 80/20 split between the two factor pairs is a
reasoned design decision based on observed variation, not a formal
statistical weighting method (e.g. inverse-variance weighting). Within
each pair, weights are split evenly (0.4/0.4 and 0.1/0.1) since no strong
evidence favours one factor over its pair partner. This is documented as
an assumption, not a calculated result — a defensible design choice, open
to revision as a future refinement.

### Score distribution and suitability levels

The scoring formula produces a right-skewed distribution: 46.7% of
scored parcels (10,037 of 21,491) score exactly 10.0. This reflects the
underlying geology of Bay of Plenty (soil_order ~65.9% Allophanic/Pumice,
soil_texture ~64.2% Loamy, soil_drainage 86.5% Well drained, soil_depth
94.1% Deep) rather than a modelling error — most parcels stack every
factor at or near its maximum.

**Consequence for business question 1:** a forced top-N ranking is
uninformative when 47% of parcels tie for first place. Instead, parcels
are grouped into suitability levels:

- Excellent: 8.0-10.0
- Good: 5.0-7.9
- Marginal: <5.0

Business question 1 is answered by reporting the % of parcels per level
and their geographic concentration by subzone, not a single ranked list.

**Boundary bug, fixed:** `05_subzone_summary.py` and
`08_regional_summary_expansion.py` originally binned scores with
`pandas.cut`'s default `right=True`, which is right-*inclusive* —
placing a score of exactly 5.0 in "Marginal" and exactly 8.0 in "Good",
both contradicting the ranges stated above (5.0 belongs in Good, 8.0 in
Excellent). This silently misclassified any parcel that scored exactly
on a tier boundary — 4,176 of 21,491 parcels (19.4%) scored exactly 8.0
and were wrongly counted as "Good". It was caught because
`expansion_candidates` (filtered on the literal `suitability_score >=
8.0`) came out *larger* than the "Excellent" count reported by
`suitability_levels_summary`, which should be structurally impossible
since candidates are a subset of the Excellent tier. Fixed by binning
with `right=False` instead, which correctly makes both the 5.0 and 8.0
boundaries left-inclusive. All figures in this document are post-fix.

**Final figures (4 TAs, post boundary-fix), region-wide, 21,491 scored
parcels:**

| Level | Parcels | % |
|---|---|---|
| Excellent | 16,414 | 76.4% |
| Good | 3,889 | 18.1% |
| Marginal | 1,188 | 5.5% |

(Full detail, including the 5-named-subzone view and its 88.8%
weighted-average Excellent share, is in "Regional summary and expansion
candidates" below.)

**Future refinement (not implemented):** once climate risk data (frost,
heavy rainfall) is ingested, it could serve as a tiebreaker within the
"Excellent" tier — parcels tied on soil suitability but with lower
climate risk would rank higher. Documented here as a known next step,
not built into the current score.

### Regional summary and expansion candidates (business questions 1 and 2)

`src/08_regional_summary_expansion.py` extends the suitability-level
breakdown above to the full dataset (not just parcels within Apophenia's
5 named subzones — that narrower view is `subzone_summary`, from
`05_subzone_summary.py`) and answers business question 2.

**Business question 1, region-wide (`suitability_levels_summary`):** of
21,491 scored parcels — Excellent 16,414 (76.4%), Good 3,889 (18.1%),
Marginal 1,188 (5.5%). This is actually *less* skewed toward "Excellent"
than the 5-named-subzone view (`subzone_summary`, weighted average
88.8% Excellent across Tauranga/Te Puke/Pongakawa/Katikati/Opotiki) — the
region-wide figure is pulled down by Whakatane District, which sits
almost entirely outside the 5 named subzones and has a more varied soil
profile than the tightly-curated Apophenia footprint.

**Business question 2, expansion candidates (`expansion_candidates`):**
parcels with `suitability_score >= 8.0` (Excellent tier) that are NOT
already classified as `lcdb_class_2023 = 'Orchard, Vineyard or Other
Perennial Crop'` — good-to-excellent soil with no current orchard/
vineyard/perennial-crop use, i.e. real expansion candidates rather than
existing orchards. Result: **13,041 parcels** (79.5% of all 16,414
Excellent-tier parcels) — most excellent-soil land in the region is not
currently under orchard/vineyard/perennial-crop use, which tracks with
LCDB's own region-wide finding that only ~3% of land cover falls in that
class (see "Parcel selection" above). Breakdown by subzone: 10,205 fall
outside the 5 named subzones, then Tauranga 1,972, Te Puke 407,
Pongakawa 251, Katikati 166, Opotiki 40.

Parcels with a NULL `lcdb_class_2023` (60 of 22,834 overall — no LCDB
match) are included as candidates, not excluded: they are not confirmed
orchard, and excluding them would silently drop otherwise-qualifying
parcels because of an LCDB coverage gap rather than because they're
actually disqualified. `expansion_candidates` stores `source_id` only
(no geometry) — geometry for mapping is looked up from
`parcels_linz.geojson` via that key when needed.

### Handling unmatched parcels (nulls)

1,343 of 22,834 parcels (5.9%) have no S-map match (soil_depth,
soil_texture, soil_drainage, soil_order all null); 60 (0.3%) have no
LCDB match. These parcels fall outside S-map's/LCDB's mapped coverage —
typically coastal/rural edge cases, not a data quality error (see
docs/data_sources.md ingestion notes). The unmatched rate has risen in
stages as scope expanded: 0.8% (2 TAs) → 5.5% (3 TAs, once Opotiki
District's more remote/coastal terrain was correctly included) → 5.9%
(4 TAs, with Whakatane District added) — each addition has pulled in
land further from the original Tauranga/Western Bay urban-fringe core,
where S-map coverage is most complete.

Decision: parcels with any null soil attribute are excluded from the
suitability score entirely, not assigned a default/imputed value.
Inventing a soil value for a parcel with no real data would undermine the
credibility of the score for every parcel, not just the affected ones.
These excluded parcels are reported separately (count + list) rather than
silently dropped, so the case study can state coverage honestly.

---

### Cross-project comparison (business question 3)

Business question 3 asks whether Apophenia's high operational risk
corridors (e.g. the Ōpōtiki-Tauranga corridor, 23% late) correlate with
low soil suitability, or whether the risk is primarily logistical rather
than agronomic.

**Method:** `src/06_cross_project_comparison.py` joins Terroir's
`subzone_summary` (mean_score per subzone, from real S-map/LCDB-derived
scoring) against `data/external/dim_corridor_apophenia.csv` (Apophenia's
per-corridor risk indicators) on subzone name, then computes the Pearson
correlation between mean_score and each of Apophenia's 3 risk indicators
(distance_port_km, base_risk_weight, psa_incidence_historical) across
the 5 shared subzones.

**Result:** mean_score correlates negatively with psa_incidence_historical
(r = -0.86) and with distance_port_km (r = -0.55), and is essentially
uncorrelated with base_risk_weight (r = 0.18). Read at face value, this
would suggest operational risk in Apophenia's model is more logistical
(distance, historical incidents) than agronomic (soil suitability) — the
subzones with the best soil scores are not obviously the ones Apophenia
flags as highest-risk.

**Critical caveat — real vs. synthetic data:** `dim_corridor_apophenia.csv`
is Apophenia's illustrative/synthetic dataset, not measured operational
data (e.g. actual freight volumes, real incident logs). Terroir's
mean_score, by contrast, is derived from real LINZ/S-map/LCDB data. This
correlation is therefore a demonstration of cross-project analytical
technique — joining and comparing two related portfolio projects — not a
validated business finding. It should not be presented as evidence that
real kiwifruit logistics risk in Bay of Plenty is agronomic vs.
logistical in origin. Any case-study write-up of this result must state
this caveat alongside the numbers, not only in supporting narrative.
Also worth noting: n=5 (one row per subzone) is far too small for the
correlation coefficients above to carry statistical weight on their own,
independent of the synthetic-data caveat.

---

## Climate risk ingestion (business question 5)

**Representative point per subzone:** rather than querying weather data
per parcel (22,834 API calls), each subzone is reduced to a single
representative point — the average centroid of every parcel assigned
that subzone (subzone IS NOT NULL, same assignment as
`03_ingest_subzones.py`). Centroids are averaged in a projected CRS
(NZTM2000, EPSG:2193) for accuracy, then the single averaged point is
converted back to WGS84 for the Open-Meteo API call. This trades
per-parcel precision for a tractable 5-call ingestion — acceptable given
Bay of Plenty's climate varies gradually across a subzone's extent
compared to the sharp parcel-to-parcel differences seen in soil data.

**Source and window:** Open-Meteo Historical Weather API (ERA5
reanalysis archive), hourly `temperature_2m` and `precipitation`,
2016-01-01 to 2025-12-31 (10 full years, local NZ timezone). Ten years
was chosen as long enough to average out year-to-year extremes (a single
unusually cold or wet year skewing a subzone's risk profile) while
staying within Open-Meteo's straightforward free-tier archive access —
no account or API key required, same as documented in
`docs/data_sources.md`.

**Metrics (`subzone_climate_risk` table, all on an annual basis):**

- **Frost days/year** — days where the daily minimum hourly temperature
  is below 0°C, averaged over the 10-year window.
- **Chill hours/year** — hours below 7°C during May-August (the kiwifruit
  dormancy window), averaged over the 10-year window.
- **Heavy rain days/year** — days where total daily precipitation exceeds
  25mm, averaged over the 10-year window.

Raw 10-year totals are kept alongside each per-year figure (e.g.
`frost_days` next to `frost_days_per_year`) for context — the totals are
easier to sanity-check against a specific historical event, while the
per-year figures are what any future scoring extension would use, since
they put all 3 climate metrics on the same basis as each other.

Not yet incorporated into `suitability_score` — see "Future refinement
(not implemented)" under Score distribution above.
