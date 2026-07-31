# Business Questions

Purpose: defines what Terroir's analysis must answer before any ingestion
or scoring code is written.

1. Which parcels within Tauranga City / Western Bay of Plenty / Opotiki
   District show the best land suitability for kiwifruit?
2. Are there areas with no current horticultural use that should be
   considered for expansion?
3. Cross-reference with Apophenia: does high operational risk (e.g.
   Ōpōtiki-Tauranga corridor, 23% late) correlate with low soil
   suitability, or is the risk primarily logistical rather than
   agronomic?
4. How does suitability rank/heat-map across the same five subzones used
   in Apophenia (Katikati, Te Puke, Tauranga, Pongakawa, Opotiki)?
5. Which zones are most exposed to climate risk (frost, heavy rainfall),
   and which show greater waterlogging vulnerability based on soil
   drainage class?

**Known limitation:** waterlogging vulnerability (Q5) uses S-map drainage
class only, not elevation/DEM. LINZ elevation data was evaluated and
excluded — see `docs/methodology.md` for reasoning.

## Status

Closed (Fase 1). These five questions guide the scoring model and
dashboard work from here.
