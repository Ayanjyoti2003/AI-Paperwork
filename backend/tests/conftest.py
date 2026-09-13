"""Pytest configuration ensuring backend directory is in sys.path."""

from __future__ import annotations

import sys
from pathlib import Path

# Add backend root directory to sys.path so 'app' is importable
# regardless of whether pytest is invoked from repo root or backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
