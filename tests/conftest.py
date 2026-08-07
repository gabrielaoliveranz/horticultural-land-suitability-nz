# =============================================================================
# TERROIR — pytest configuration
# Script: tests/conftest.py
# Stage:  Testing
# Author: Gabriela Olivera | Data Analytics Portfolio
# =============================================================================
"""
Adds src/ to sys.path so the pipeline scripts (calculate_score.py,
regional_summary_expansion.py, ...) can be imported directly by name —
they're plain scripts, not an installed package.
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
