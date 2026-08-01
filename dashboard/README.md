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
│   ├── 1_Overview.py            # stub
│   ├── 2_Suitability_Map.py     # stub
│   ├── 3_Expansion_Candidates.py # stub
│   ├── 4_Apophenia_Comparison.py # stub
│   └── 5_Climate_Risk.py        # stub
└── README.md
```

## Status

Skeleton in place, 1 of 6 pages built:

- `0_Intro.py` — **built**. One-line description, link to Apophenia
  (sister project), the real differentiator (from `PRODUCT.md`'s
  Positioning section), and a link into Overview.
- `1_Overview.py`, `2_Suitability_Map.py`, `3_Expansion_Candidates.py`,
  `4_Apophenia_Comparison.py`, `5_Climate_Risk.py` — **stubs**: title +
  "Under construction" only, enough for navigation to work end-to-end.
  Each stub's docstring notes which `terroir.db` table/business question
  it will eventually present.

## Running locally

```
streamlit run dashboard/streamlit_app.py
```
