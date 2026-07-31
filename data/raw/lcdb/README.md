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

**Status:** Source confirmed (Fase 2 exploration). No data ingested yet.
