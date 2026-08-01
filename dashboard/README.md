# Dashboard

The Terroir analytical dashboard, built in Streamlit. See
`docs/methodology.md` for why Streamlit was chosen over Power BI.

## Structure

Multipage app using `st.Page` + `st.navigation` (the current recommended
pattern, Streamlit >= 1.36) — not the older auto-discovered `pages/`
directory convention, though page files still live under `pages/` with
numbered filenames for readability. Routing and order are controlled
explicitly in `streamlit_app.py`, not inferred from filenames.

```
dashboard/
├── streamlit_app.py            # entrypoint — defines pages, calls st.navigation
├── pages/
│   ├── 0_Intro.py               # built — landing page
│   ├── 1_Overview.py            # built — KPI row + region-wide chart
│   ├── 2_Suitability_Map.py     # built — parcel-level pydeck map
│   ├── 3_Expansion_Candidates.py # built — pydeck map, LCDB-colored
│   ├── 4_Apophenia_Comparison.py # built — cross-project comparison
│   └── 5_Climate_Risk.py        # built — frost/chill/rain by subzone
└── README.md
```

## Status

6 of 6 pages built:

- `0_Intro.py` — **built**. One-line description, link to Apophenia
  (sister project), the real differentiator (from `PRODUCT.md`'s
  Positioning section), and a link into Overview.
- `1_Overview.py` — **built**. KPI row (parcels ingested, parcels
  scored, % Excellent) from `suitability_levels_summary` /
  `parcel_scores` / `parcel_attributes`, plus a bar chart of the
  region-wide Excellent/Good/Marginal split.
- `2_Suitability_Map.py` — **built**. Parcel-level pydeck GeoJsonLayer
  map, geometry from `parcels_linz.geojson` joined with
  `suitability_score`/`subzone` from `parcel_scores`, colored by level,
  with a subzone filter (5 named Apophenia subzones + "All") and a
  hover tooltip. Full precision genuinely exceeded Streamlit's 200MB
  message size limit for the "All" view (229MB) — geometry is
  simplified (~1m tolerance) and coordinates rounded (6dp) in the cached
  loader; see the page's own docstring for the numbers.
- `3_Expansion_Candidates.py` — **built**. Parcel-level pydeck map of
  `expansion_candidates`, colored/filterable by LCDB class instead of
  suitability level (subzone filter + LCDB class filter, both with
  "All"), hover tooltip, spinner on load. Excludes urban/settlement LCDB
  classes at the display layer (13,041 → 11,383 shown) — a known gap in
  the underlying `expansion_candidates` table itself, logged in
  `docs/methodology.md` as a refinement still to push back into
  `08_regional_summary_expansion.py`.
- `4_Apophenia_Comparison.py` — **built**. Business question 3:
  `cross_project_comparison` (5 subzones) shown as a real-vs-synthetic
  table (Terroir's `mean_score` next to Apophenia's 3 synthetic risk
  indicators), with correlations computed live from the loaded table
  (not hardcoded) and plain-language interpretation for each, including
  the near-zero one explicitly labeled "no meaningful relationship." A
  prominent `st.warning()` disclaimer sits at the top, and the -0.86
  PSA-incidence correlation carries its own caveat about Opotiki's
  outlier influence — recomputed without Opotiki (r = -0.76, n=4) to
  confirm the correlation survives removing it rather than assuming.
- `5_Climate_Risk.py` — **built**. Business question 5:
  `subzone_climate_risk` (5 subzones) shown as a table of the 3
  annualized metrics (frost days/year, chill hours/year avg, heavy rain
  days/year), with the raw 10-year totals for frost and heavy rain
  tucked into an expander (chill hours has no raw-total column, only
  the average). Interpretation covers near-zero frost region-wide, the
  coastal-vs-inland chill-hour split (grounded in the subzones' own
  lat/lon and known geography, not just the numbers), and Opotiki's
  standout heavy-rain frequency.

## Known issues

- **Overview (and other pages): direct URL navigation to a non-default
  page (e.g. loading `http://localhost:8501/Overview` fresh, rather than
  clicking through from the sidebar) triggers harmless 404 console
  errors** for `_stcore/health` and `_stcore/host-config` — Streamlit's
  frontend resolves those internal endpoints relative to the current
  path instead of root when the page is deep-linked directly. Confirmed
  this doesn't affect real usage (root load + sidebar navigation is
  always clean) — flagged for the final polish pass, not forgotten.
- **Suitability Map: the pydeck basemap renders dark (CARTO's default
  dark-matter style), clashing with the rest of the app's light
  `#E8E8E3` theme.** pydeck/deck.gl's map style isn't controlled by
  `.streamlit/config.toml` — it needs its own explicit light-style
  `map_style` on the `pydeck.Deck` object. Flagged for the final polish
  pass, along with the footer and button styling — not forgotten.

## Design notes

- **Expansion Candidates: ~52% of subzone x LCDB-class filter
  combinations return zero results (69 of 132 possible pairs) — this is
  expected, not a data gap.** Smaller subzones only have a handful of
  the 22 LCDB classes present at all (Opotiki 3, Katikati 4, Pongakawa
  6), so most combinations are legitimately empty. The page shows a
  clear "No candidates match..." message for these rather than an empty
  or broken map — see the page's own docstring for how this was
  confirmed (and the crash it used to cause before the empty-state
  check was added).

## Running locally

```
streamlit run dashboard/streamlit_app.py
```
