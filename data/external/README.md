# External data

Supplementary reference datasets from sources other than LINZ, S-map, or
the primary climate source (Open-Meteo) — e.g. Stats NZ regional data.

## Files

- `dim_corridor_apophenia.csv` — 5 rows, one per Apophenia corridor
  (Te Puke, Katikati, Tauranga, Pongakawa, Opotiki): highway,
  distance_port_km, congestion_index_avg, base_risk_weight,
  psa_incidence_historical. From Apophenia (Gabriela Olivera's kiwifruit
  export risk simulator, the sister project this data is imported from).
  **This is Apophenia's illustrative/synthetic risk data, not measured
  operational data** (real freight volumes, real incident logs) — see
  `docs/methodology.md`, "Cross-project comparison (business question
  3)" for the full caveat governing how any result using this file may
  be interpreted. Used by `src/cross_project_comparison.py`.

## Status

One external dataset added (see "Files" above) for the business
question 3 cross-project comparison. No other external datasets added
yet.
