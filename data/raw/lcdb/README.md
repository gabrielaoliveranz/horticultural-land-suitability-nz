# LCDB (Land Cover Database)

Purpose: real land-use classification for each parcel, used as an
attribute (not a filter) alongside the area threshold — see
docs/methodology.md, "Parcel selection: area threshold + LCDB as
attribute, not filter".

**Access:** LRIS Portal (lris.scinfo.org.nz), layer 123148 — LCDB v6.0,
same LRIS_API_KEY as S-map. WFS 2.0.0.

**Field used:** `Name_2023` (most recent survey, 2023/24 imagery).
Target class: "Orchard, Vineyard or Other Perennial Crop" (code 33).

**Licence:** Creative Commons, by Manaaki Whenua — Landcare Research.
Flagged, not resolved: `docs/data_sources.md`'s S-map section states an
"open licence" explicitly scoped to its own 4 layers only — it doesn't
separately confirm LCDB's licence, so this line and that file aren't
fully reconciled. Left as-is here rather than silently deciding which
is right.

**Status:** Source confirmed (Fase 0/2 exploration). Ingestion is
complete (`src/ingest_soil_lcdb.py`, 99.7% match rate) — this folder
stays empty by design, not because ingestion hasn't happened: the
pipeline fetches WFS responses live on each run and writes straight to
`parcel_attributes.lcdb_class_2023` in `data/processed/terroir.db`, it
never caches a raw copy here.
