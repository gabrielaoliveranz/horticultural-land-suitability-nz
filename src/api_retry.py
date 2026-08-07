# =============================================================================
# TERROIR — Bounded-retry HTTP GET helper
# Script: api_retry.py
# Stage:  Ingestion (shared utility)
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Wraps requests.get() with bounded exponential-backoff retries for
transient failures only: connection errors, timeouts, HTTP 429, and any
HTTP 5xx. A 4xx response other than 429 (bad API key, malformed CQL
filter, etc.) is never retried — raise_for_status() is called immediately
so that kind of failure surfaces right away instead of being masked
behind a retry loop that can't fix a client-side mistake.

Used by ingest_linz.py and ingest_climate_risk.py. See
docs/methodology.md, "Retry policy for API ingestion" for the reasoning
behind the specific bounds used here. Kept dependency-light: stdlib
`time` plus the `requests` exceptions the codebase already depends on —
no new third-party retry library.
"""

import time

import requests

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def get_with_retry(url, params=None, timeout=60, max_retries=4, backoff_base_seconds=1.0):
    attempt = 0
    while True:
        attempt += 1
        try:
            response = requests.get(url, params=params, timeout=timeout)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            if attempt > max_retries:
                raise
            _wait_before_retry(attempt, backoff_base_seconds, reason=type(exc).__name__)
            continue

        if response.status_code in RETRYABLE_STATUS_CODES and attempt <= max_retries:
            _wait_before_retry(
                attempt, backoff_base_seconds,
                reason=f"HTTP {response.status_code}",
                retry_after=response.headers.get("Retry-After"),
            )
            continue

        # Raises immediately for any other 4xx (or the final retryable
        # failure once max_retries is exhausted) — never retried further.
        response.raise_for_status()
        return response


def _wait_before_retry(attempt, backoff_base_seconds, reason, retry_after=None):
    if retry_after is not None:
        try:
            delay = float(retry_after)
        except ValueError:
            delay = backoff_base_seconds * (2 ** (attempt - 1))
    else:
        delay = backoff_base_seconds * (2 ** (attempt - 1))

    print(f"  {reason} — retrying in {delay:.1f}s (attempt {attempt})...")
    time.sleep(delay)
