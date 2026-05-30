"""ESIOS HTTP client.

Base URL: https://api.esios.ree.es
Auth: x-api-key header with ESIOS_TOKEN.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

from spanish_grid_mcp.cache import cache

ESIOS_BASE_URL = "https://api.esios.ree.es"
ESIOS_TOKEN = os.getenv("ESIOS_TOKEN", "")

_HEADERS = {
    "Accept": "application/json; application/vnd.esios-api-v1+json",
    "x-api-key": ESIOS_TOKEN,
}


def is_configured() -> bool:
    return bool(ESIOS_TOKEN)


async def fetch_indicator(
    indicator_id: int,
    start_date: str,
    end_date: str,
    time_trunc: str | None = None,
) -> dict[str, Any]:
    url = f"{ESIOS_BASE_URL}/indicators/{indicator_id}"
    params: dict[str, str] = {"start_date": start_date, "end_date": end_date}
    if time_trunc:
        params["time_trunc"] = time_trunc

    cache_key = str(("esios:fetch_indicator", url, params))
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()

    cache.set(cache_key, data)
    return data


async def search_indicators(query: str, limit: int = 10) -> dict[str, Any]:
    url = f"{ESIOS_BASE_URL}/indicators"
    params: dict[str, str] = {"text": query}

    cache_key = str(("esios:search_indicators", url, params))
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()

    results = data.get("indicators", [])
    results = results[:limit]
    data["indicators"] = results

    cache.set(cache_key, data)
    return data
