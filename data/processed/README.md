# Processed data

Cleaned datasets, joined across sources by subzone/grid ID, ready for
analysis and modelling.

## Status

Fase 2 ingestion and Fase 3 scoring complete. Two files generated so far
(seven tables total in `terroir.db`):

- `parcels_linz.geojson` — `src/ingest_linz.py` (LINZ Property
  Boundaries, all 4 target TAs + 1 ha area filter, 22,834 parcels:
  Western Bay of Plenty District 11,028, Whakatane District 5,434,
  Tauranga City 3,237, Ōpōtiki District 3,135).
- `terroir.db` (SQLite), seven tables:
  - `parcel_attributes` — `src/ingest_soil_lcdb.py` +
    `src/ingest_subzones.py` (keyed on `source_id`, not `parcel_id` —
    see script docstrings): soil_depth, soil_texture, soil_drainage,
    soil_order (94.1% match), lcdb_class_2023 (99.7% match), and subzone
    (18.0% match — only parcels within Apophenia's 5 named subzones get
    one, by design; Whakatane District isn't one of them, so it's almost
    entirely NULL here). See `docs/methodology.md`, "Handling unmatched
    parcels (nulls)".
  - `parcel_scores` — `src/calculate_score.py` (keyed on
    `source_id`): suitability_score (0-10) plus the per-factor points
    and weights it's built from, for 21,491 parcels (the 1,343 with a
    null soil attribute are excluded, not scored). See
    `docs/methodology.md`, "Point tables" / "Weights" / "Score
    distribution and suitability levels".
  - `subzone_summary` — `src/subzone_summary.py` (keyed on
    `subzone`): parcel count, mean score, and %
    Excellent/Good/Marginal per subzone, for the 4,103 scored parcels
    within the 5 named subzones.
  - `cross_project_comparison` — `src/cross_project_comparison.py`
    (keyed on `subzone`): Terroir's mean_score joined against
    Apophenia's corridor risk indicators, plus the Pearson correlation
    between them. See `docs/methodology.md`, "Cross-project comparison
    (business question 3)" for the real-vs-synthetic caveat.
  - `subzone_climate_risk` — `src/ingest_climate_risk.py` (keyed on
    `subzone`): frost days, chill hours, and heavy rain days (2016-2025,
    raw totals plus per-year figures) at one representative point per
    subzone. Unaffected by the Whakatane District scope expansion (not
    one of the 5 named subzones this table is keyed on), so not
    re-run — see `docs/methodology.md`, "Climate risk ingestion
    (business question 5)".
  - `suitability_levels_summary` — `src/regional_summary_expansion.py`
    (keyed on `suitability_level`): count and % Excellent/Good/Marginal
    across all 21,491 scored parcels region-wide (Excellent 76.4%, Good
    18.1%, Marginal 5.5%) — the full-region counterpart to
    `subzone_summary`'s 5-named-subzone view (which runs noticeably
    higher, 88.9% weighted-average Excellent, since Whakatane pulls the
    region-wide figure down).
  - `expansion_candidates` — `src/regional_summary_expansion.py`
    (keyed on `source_id`, no geometry — join back to
    `parcels_linz.geojson` for mapping): the 13,040 parcels with
    suitability_score >= 8.0 that aren't already LCDB-classified as
    orchard/vineyard/perennial crop. See `docs/methodology.md`,
    "Regional summary and expansion candidates (business questions 1
    and 2)".

**Fixed boundary bug (see `docs/methodology.md`, "Score distribution and
suitability levels"):** `subzone_summary` and `suitability_levels_summary`
originally misclassified any parcel scoring exactly 5.0 or 8.0 into the
lower tier, due to a `pandas.cut` default. Fixed and re-run — all figures
above are post-fix.

Both files are committed to git via **Git LFS** (see `.gitattributes`)
— large enough that a normal git blob wasn't a good fit, but small
enough (~40MB combined) to stay well within GitHub's free LFS quota.
This means they're present on disk on every deploy, including a fresh
Streamlit Cloud clone, with no ingestion-on-first-load step needed —
an earlier version of this repo ran the pipeline live on cold start
instead (`dashboard/bootstrap.py`), removed once the data itself
started shipping with the repo via LFS.

## Reproducing this data

If you need to regenerate these files from scratch (e.g. after a
scope/methodology change), run the scripts in `src/` in order
(`python src/ingest_linz.py`, then `ingest_soil_lcdb.py`,
`ingest_subzones.py`, `calculate_score.py`,
`subzone_summary.py`, `cross_project_comparison.py`,
`ingest_climate_risk.py`, and `regional_summary_expansion.py`).
Requires a `.env` with valid API keys — see docs/data_sources.md. The
regenerated files overwrite what's already here; commit them the same
way as any other change (Git LFS picks them up automatically via the
`.gitattributes` tracking rule, no extra step needed).
