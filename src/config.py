# =============================================================================
# TERROIR — Shared paths and configuration
# Script: config.py
# Stage:  Shared utility
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Single source of truth for PROJECT_ROOT, DB_PATH, and the processed/
external data paths every ingestion/scoring script and dashboard page
needs. Seven pipeline scripts each used to redefine
`PROJECT_ROOT = Path(__file__).resolve().parent.parent` with their own
DB_PATH — a single relocation of the database would have required
seven (plus five dashboard pages) coordinated edits. Import from here
instead; never redefine these locally.

Also provides get_connection(), a thin context-manager wrapper around
sqlite3.connect() so the ~15 call sites across the codebase share one
place to change connection behaviour (e.g. adding row_factory) later.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

DATA_DIR: Path = PROJECT_ROOT / "data"
DATA_PROCESSED_DIR: Path = DATA_DIR / "processed"
DATA_EXTERNAL_DIR: Path = DATA_DIR / "external"

DB_PATH: Path = DATA_PROCESSED_DIR / "terroir.db"
PARCELS_PATH: Path = DATA_PROCESSED_DIR / "parcels_linz.geojson"
CORRIDOR_CSV_PATH: Path = DATA_EXTERNAL_DIR / "dim_corridor_apophenia.csv"


@contextmanager
def get_connection(db_path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    """Context-managed sqlite3 connection, defaulting to DB_PATH."""
    with sqlite3.connect(db_path) as conn:
        yield conn
