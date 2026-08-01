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
│   ├── 3_Expansion_Candidates.py # stub
│   ├── 4_Apophenia_Comparison.py # stub
│   └── 5_Climate_Risk.py        # stub
└── README.md
```

## Status

3 of 6 pages built:

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
- `3_Expansion_Candidates.py`, `4_Apophenia_Comparison.py`,
  `5_Climate_Risk.py` — **stubs**: title + "Under construction" only,
  enough for navigation to work end-to-end. Each stub's docstring notes
  which `terroir.db` table/business question it will eventually present.

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

## Running locally

```
streamlit run dashboard/streamlit_app.py
```
