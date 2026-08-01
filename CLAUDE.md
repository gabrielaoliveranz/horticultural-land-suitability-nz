## Stale-number audits

Whenever a fix changes a reported number (counts, percentages, thresholds,
layer IDs), before marking the task done: grep the whole repo for the old
value and list every file that references it — even files not named in the
original request. Include this in the same summary, don't wait to be asked.

## Data integrity

- **Verify join keys are actually unique** before using them to merge
  tables: check `COUNT(*) == COUNT(DISTINCT key)` empirically. Never
  assume a field is unique because of its name (e.g. "parcel_id").
- **Never hardcode field names or category codes from memory or
  documentation.** Always confirm against a live sample response from
  the actual API/source before hardcoding.
- **Request explicit CRS on any new geospatial source**, and verify it
  against the response's own declared CRS field — never assume WGS84
  by default.
- **NZ place names: always use the `_ascii` field when available**
  (e.g. `territorial_authority_ascii`, `name_ascii`). Official names may
  contain macrons that silently break exact-string filters.
- **On any data-integrity bug (not just coverage gaps): stop and ask
  before modifying already-committed files.** Coverage gaps (missing
  data) can be reported and handled inline; integrity bugs (wrong data
  silently written) require explicit confirmation first.

## Git hygiene

- **Separate commits for fixes vs. features** — never mixed in one commit.
- **Local vs. pushed history:** amending commit messages or rebasing is
  safe while nothing has been pushed. Once pushed, treat history as
  immutable — don't rewrite it without being explicitly asked.
