"""Disk cache used by the HTTP clients.

ESIOS / REE / AEMET data is immutable once published, so we cache aggressively
keyed by URL + query params. The first call fetches; everything after that is
served from disk until the cache is cleared.
"""
from __future__ import annotations

import os
from pathlib import Path

from diskcache import Cache

_DEFAULT_DIR = Path.home() / ".cache" / "spanish-grid-mcp"
CACHE_DIR = Path(os.getenv("SPANISH_GRID_CACHE_DIR", _DEFAULT_DIR))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

cache = Cache(str(CACHE_DIR))
