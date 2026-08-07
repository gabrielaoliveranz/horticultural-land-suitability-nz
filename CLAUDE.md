## Spelling convention (en-NZ)

This project uses en-NZ spelling throughout — documented as a fact in
`PRODUCT.md`'s "Capabilities and Constraints" ("Writing conventions:
en-NZ spelling throughout"), but never promoted here as a checked rule
until a US-spelling pass was requested explicitly rather than caught
proactively. Treat it the same as the stale-number audit below: a
standing check, not something to wait to be asked for.

Whenever writing or editing any user-facing copy, docstring, or
comment: use en-NZ spelling (colour, behaviour, organise, analyse,
centre, licence as a noun, catalogue, travelled — not the US
equivalents). Before marking a copy-writing or documentation task
done, grep the changed file(s) for common US patterns (`-ize`/`-ide`
endings where NZ uses `-ise`, `-or` where NZ uses `-our`, `-er` where
NZ uses `-re`, `-yze` where NZ uses `-yse`) and fix any found — include
the list of instances found and fixed in the same summary, don't wait
to be asked.

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

## Testing (Playwright/Streamlit)

- **Never use `waitUntil: 'networkidle'` on a Streamlit app.** Streamlit
  holds a persistent WebSocket open for live reactivity, so network
  activity never truly goes idle — the wait reliably times out (seen on
  the Suitability Map page). Use `waitUntil: 'load'`, then poll
  explicitly for the target element (e.g. `[data-testid="stException"]`
  or the specific chart/test-id you expect) instead of trusting a single
  post-load check.
- **A single early check for `stException` can false-negative.** Heavy
  renders (large pydeck charts, big dataframes) serialize/transfer
  asynchronously — an error can surface seconds after the page looks
  "loaded." Poll in a loop for either the exception or the expected
  success element, don't check once and move on (this is exactly how
  the Suitability Map's real MessageSizeError was almost missed).
- **Any dashboard page with a map must include a loading spinner**
  (`st.spinner(...)`) around the data-load/render step, matching the
  pattern established on `2_Suitability_Map.py`. Apply this from the
  start on new map pages, without being asked each time.

## Git hygiene

- **Separate commits for fixes vs. features** — never mixed in one commit.
- **Local vs. pushed history:** amending commit messages or rebasing is
  safe while nothing has been pushed. Once pushed, treat history as
  immutable — don't rewrite it without being explicitly asked.

## Python engineering standards

These are standing checks, not one-off tasks — apply them to every new
script and every edit, without being asked each time.

- **Logging, not `print()`.** Pipeline scripts in `src/` report progress
  through the stdlib `logging` module with a shared configuration: INFO
  for progress, WARNING for retries and coverage gaps, ERROR for
  failures. Bare `print()` was the original pattern across all eight
  scripts and gave no levels, no timestamps, and no way to silence
  output under test. Streamlit's own `st.*` output in `dashboard/` is
  exempt — this applies to the pipeline only.
- **Type hints on every function signature.** Both in `src/` and in
  tests. Hints only; no type checker runs in CI.
- **PEP 8, including the 79-character line limit.** Never widen a line
  past it for convenience — restructure instead.

## Tests ship with the logic

New pure or logic-dense functions are tested in the same commit that
introduces them — never "later". `api_retry.py` was added with bounded
retries, exponential backoff, `Retry-After` parsing and 4xx-vs-5xx
branching, and shipped with zero coverage in the very commit series that
added the project's first tests. Reviewing my own work caught it; a rule
would have prevented it.

Tests must run on a clean clone with no data present: use small
in-memory fixtures, never read `terroir.db` or `parcels_linz.geojson`.
Any bug found and fixed in a calculation gets a regression test naming
the bug, in the style of the `pandas.cut` left-inclusive binning test.

## Paths and configuration have one home

`PROJECT_ROOT`, `DB_PATH` and the processed-data paths live in
`src/config.py` and are imported from there. Seven scripts each
redefined `PROJECT_ROOT = Path(__file__).resolve().parent.parent` with
their own `DB_PATH`, meaning a single relocation of the database would
have required seven coordinated edits. Never redefine these locally.

## Dependency and deployment discipline

Every package imported directly anywhere in `src/` or `dashboard/` is
declared explicitly in `requirements.txt` and pinned — never left to
resolve as a transitive dependency of `geopandas` or `streamlit`.

Exact pins are a known cause of build failures on Streamlit Community
Cloud. After any change to `requirements.txt`, confirm the pins resolve
on the Python version that platform uses for this app. If a pin cannot
resolve, stop and ask — never silently loosen one.
