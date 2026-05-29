"""ESIOS HTTP client (stub).

Base URL: https://api.esios.ree.es
Auth: x-api-key header with ESIOS_TOKEN.

Real implementation will hit /indicators/{id}, /indicators (search), etc.
"""
from __future__ import annotations

import os

ESIOS_BASE_URL = "https://api.esios.ree.es"
ESIOS_TOKEN = os.getenv("ESIOS_TOKEN", "")


def is_configured() -> bool:
    return bool(ESIOS_TOKEN)
