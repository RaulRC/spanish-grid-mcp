"""AEMET OpenData HTTP client.

Base URL: https://opendata.aemet.es/opendata/api
Auth: api_key query param with AEMET_TOKEN.

AEMET uses a two-step pattern: the first request returns a JSON with a 'datos'
field containing the URL to the actual data payload. The second request fetches
that URL.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

from spanish_grid_mcp.cache import cache

AEMET_BASE_URL = "https://opendata.aemet.es/opendata/api"
AEMET_TOKEN = os.getenv("AEMET_TOKEN", "")

_AEMET_HEADERS = {"Cache-Control": "no-cache"}


def is_configured() -> bool:
    return bool(AEMET_TOKEN)


async def _two_step_fetch(endpoint: str) -> list[dict[str, Any]]:
    api_url = f"{AEMET_BASE_URL}{endpoint}"
    params = {"api_key": AEMET_TOKEN}

    cache_key_step1 = str(("aemet:step1", api_url))
    cached_url = cache.get(cache_key_step1)
    if cached_url is not None:
        data_url: str = cached_url
    else:
        async with httpx.AsyncClient() as client:
            resp = await client.get(api_url, params=params, headers=_AEMET_HEADERS, timeout=30)
            resp.raise_for_status()
            body: dict[str, Any] = resp.json()
        if body.get("estado") != 200:
            desc = body.get("descripcion", "unknown error")
            raise RuntimeError(f"AEMET API error: {desc}")
        data_url = body.get("datos", "")
        if not data_url:
            raise RuntimeError("AEMET response missing 'datos' URL")
        cache.set(cache_key_step1, data_url)

    cache_key_step2 = str(("aemet:step2", data_url))
    cached_data = cache.get(cache_key_step2)
    if cached_data is not None:
        return cached_data

    async with httpx.AsyncClient() as client:
        resp = await client.get(data_url, timeout=60)
        resp.raise_for_status()
        data: list[dict[str, Any]] = resp.json()

    cache.set(cache_key_step2, data)
    return data


async def list_stations(region: str | None = None) -> list[dict[str, Any]]:
    if region:
        endpoint = f"/observacion/convencional/estaciones/{region}"
    else:
        endpoint = "/observacion/convencional/todas"
    return await _two_step_fetch(endpoint)


async def fetch_observations(
    station_id: str,
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    endpoint = f"/observacion/convencional/datos/estacion/{station_id}"
    api_url = f"{AEMET_BASE_URL}{endpoint}"
    params = {
        "api_key": AEMET_TOKEN,
        "fechaIni": start_date,
        "fechaFin": end_date,
    }

    cache_key_step1 = str(("aemet:step1", endpoint, start_date, end_date))
    cached_url = cache.get(cache_key_step1)
    if cached_url is not None:
        data_url: str = cached_url
    else:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                api_url, params=params, headers=_AEMET_HEADERS, timeout=30
            )
            resp.raise_for_status()
            body: dict[str, Any] = resp.json()
        if body.get("estado") != 200:
            desc = body.get("descripcion", "unknown error")
            raise RuntimeError(f"AEMET API error: {desc}")
        data_url = body.get("datos", "")
        if not data_url:
            raise RuntimeError("AEMET response missing 'datos' URL")
        cache.set(cache_key_step1, data_url)

    cache_key_step2 = str(("aemet:step2", data_url))
    cached_data = cache.get(cache_key_step2)
    if cached_data is not None:
        return cached_data

    async with httpx.AsyncClient() as client:
        resp = await client.get(data_url, timeout=60)
        resp.raise_for_status()
        data: list[dict[str, Any]] = resp.json()

    cache.set(cache_key_step2, data)
    return data
