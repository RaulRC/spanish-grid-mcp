"""AEMET OpenData HTTP client.

Base URL: https://opendata.aemet.es/opendata/api
Auth: api_key query param with AEMET_TOKEN.

AEMET uses a two-step pattern: the first request returns a JSON with a 'datos'
field containing the URL to the actual data payload. The second request fetches
that URL.

Responses use ISO-8859-15 encoding; we decode from raw bytes.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

from spanish_grid_mcp.cache import cache

AEMET_BASE_URL = "https://opendata.aemet.es/opendata/api"
AEMET_TOKEN = os.getenv("AEMET_TOKEN", "")

_AEMET_HEADERS = {"Cache-Control": "no-cache"}

# ISO autonomous community codes → list of province names as returned by AEMET
_REGION_FILTERS: dict[str, list[str]] = {
    "AN": ["ALMERIA", "CADIZ", "CORDOBA", "GRANADA", "HUELVA", "JAEN", "MALAGA", "SEVILLA"],
    "AR": ["HUESCA", "TERUEL", "ZARAGOZA"],
    "AS": ["ASTURIAS"],
    "CB": ["CANTABRIA"],
    "CE": ["CEUTA"],
    "CL": ["AVILA", "BURGOS", "LEON", "PALENCIA", "SALAMANCA", "SEGOVIA", "SORIA", "VALLADOLID", "ZAMORA"],
    "CM": ["ALBACETE", "CIUDAD REAL", "CUENCA", "GUADALAJARA", "TOLEDO"],
    "CN": ["LAS PALMAS", "SANTA CRUZ DE TENERIFE", "STA. CRUZ DE TENERIFE"],
    "CT": ["BARCELONA", "GIRONA", "LLEIDA", "TARRAGONA"],
    "EX": ["BADAJOZ", "CACERES"],
    "GA": ["A CORUÑA", "LUGO", "OURENSE", "PONTEVEDRA"],
    "IB": ["BALEARES", "ILLES BALEARS"],
    "MC": ["MURCIA"],
    "MD": ["MADRID"],
    "ML": ["MELILLA"],
    "NC": ["NAVARRA"],
    "PV": ["ARABA/ALAVA", "BIZKAIA", "GIPUZKOA"],
    "RI": ["LA RIOJA"],
    "VC": ["ALICANTE", "CASTELLON", "VALENCIA"],
}


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
        charset = resp.encoding or "ISO-8859-15"
        text = resp.content.decode(charset)
        data: list[dict[str, Any]] = _decode_aemet(text)

    cache.set(cache_key_step2, data)
    return data


def _decode_aemet(text: str) -> list[dict[str, Any]]:
    """Parse AEMET response, handling ISO-8859-15 encoding."""
    import json

    text = text.replace("\\'", "'")
    return json.loads(text)


async def list_stations(region: str | None = None) -> list[dict[str, Any]]:
    data = await _two_step_fetch("/valores/climatologicos/inventarioestaciones/todasestaciones")
    result = []
    for s in data:
        row = {
            "idema": s.get("indicativo", ""),
            "nombre": s.get("nombre", ""),
            "provincia": s.get("provincia", ""),
            "latitud": s.get("latitud"),
            "longitud": s.get("longitud"),
            "altitud": s.get("altitud"),
        }
        result.append(row)
    if region is not None:
        provinces = _REGION_FILTERS.get(region.upper())
        if provinces is not None:
            result = [s for s in result if s["provincia"] in provinces]
    return result


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
        charset = resp.encoding or "ISO-8859-15"
        text = resp.content.decode(charset)
        data: list[dict[str, Any]] = _decode_aemet(text)

    cache.set(cache_key_step2, data)
    return data
