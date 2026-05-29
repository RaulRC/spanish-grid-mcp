"""AEMET OpenData HTTP client (stub).

Base URL: https://opendata.aemet.es/opendata/api
Auth: api_key query param with AEMET_TOKEN.

AEMET's pattern is two-step: first request returns a URL pointing to the
actual data payload, which you then fetch separately.
"""
from __future__ import annotations

import os

AEMET_BASE_URL = "https://opendata.aemet.es/opendata/api"
AEMET_TOKEN = os.getenv("AEMET_TOKEN", "")


def is_configured() -> bool:
    return bool(AEMET_TOKEN)
