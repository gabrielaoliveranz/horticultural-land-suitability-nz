# Terroir — Project Conventions

This file defines the standards every file in this project must follow.
Written in Fase 0, before any code — not discovered along the way.

---

## File header standard

Every `.sql` file starts with:

```sql
-- Q#: Descriptive title of what this query answers
-- Author: Gabriela Olivera | Data Analytics Portfolio
-- Data: <source file or table this query runs against>

<blank line, then the SQL>
```

Every `.py` file starts with:

```python
# =============================================================================
# TERROIR — <short module purpose>
# Script: <filename>
# Stage:  <pipeline stage, e.g. Ingestion / Cleaning / Scoring>
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
```

Every `.md` file inside `docs/` starts with a one-line purpose statement
directly under the H1 title (what this file is for, in plain language).

No exceptions. If a file doesn't fit the template, flag it before writing —
don't invent a new format on the fly.

---

## Naming rule for anything with more than one version

If a file, table, or dataset has more than one version (v1/v2, legacy/current,
draft/final), the version goes **in the filename itself**, never only in a
README:

- ✅ `soil_scoring_v1.sql`, `soil_scoring_v2.sql`
- ✅ `smap_data_legacy.csv`, `smap_data_current.csv`
- ❌ `soil_scoring.sql` (with the version explained only in a README somewhere)

Rationale: README files get out of sync. Filenames don't lie about which
version they are.

---

## Golden rule: structure change = same-commit doc update

Any commit that renames a folder, moves a file, or changes a schema MUST
update every README/doc file that references the old structure **in that
same commit** — not "later," not "next session."

Before committing a structural change, grep the whole repo for the old
path/name to catch every reference. This single rule would have prevented
most of the documentation drift found in the Apophenia project.

---

## Output paths must be asserted, not just documented

Any script that writes results to disk must end with a check that fails
loudly if the output directory doesn't match what's documented, e.g.:

```python
assert OUTPUT_DIR.exists(), f"Expected output dir {OUTPUT_DIR} not found — check path"
```

This prevents a script from silently writing to a stale path after a
folder reorganisation (this exact bug happened in Apophenia's
`05_sql_analysis.py`).

---

## Dashboard/export hygiene

Before exporting any dashboard view (screenshot, PDF, etc.):
1. Clear all active filters/selections first.
2. Confirm the KPIs show the expected totals (not a filtered subset)
   before capturing.

Applies to Power BI, Streamlit, or any BI tool used for this project.

---

## Third-party assets — log at time of use, not at the end

Any icon, image, dataset, or asset from a third party gets logged in
`docs/attributions.md` **the moment it's downloaded/used** — not
reconstructed from memory at the end of the project. Format:

```markdown
- <Asset name> by <Author> — <Source> (<URL>)
```

---

## Data source decision — lock it in Fase 0

Before writing any ingestion code, confirm for each data source (LINZ,
S-map, NIWA) whether it offers a real API or requires manual download,
and document it in `docs/data_sources.md`. Don't start coding against an
assumed API that turns out not to exist.

---

## Dashboard tool — decide once, in Fase 0, don't switch mid-project

Choose Power BI or Streamlit before Fase 5, based on which skill this
project should demonstrate (BI tool depth vs. Python/pandas end-to-end).
Document the choice and the reason in `docs/methodology.md`. Do not
revisit this decision once Fase 2 (data ingestion) has started.

---

## Real geospatial data only

Prefer shapefiles/GeoJSON over standalone lat/long pairs wherever the
source supports it — this is what makes the spatial handling read as
technically credible to a GIS-literate reviewer.
