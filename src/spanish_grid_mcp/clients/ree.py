"""REE apidatos HTTP client.

Base URL: https://apidatos.ree.es
No auth required.

Endpoints follow the pattern /es/datos/{category}/{widget} with query params
start_date, end_date, time_trunc.
"""
from __future__ import annotations

from typing import Any

import httpx

from spanish_grid_mcp.cache import cache

REE_BASE_URL = "https://apidatos.ree.es"

_WIDGETS: dict[str, tuple[str, str]] = {
    "demand:real": ("demanda", "evolucion"),
    "demand:forecast": ("demanda", "prevision"),
    "demand:scheduled": ("demanda", "programada"),
    "generation": ("generacion", "evolucion"),
    "flows": ("intercambios", "evolucion"),
    "flows:FR": ("intercambios", "evolucion-francia"),
    "flows:PT": ("intercambios", "evolucion-portugal"),
    "flows:MA": ("intercambios", "evolucion-marruecos"),
    "flows:AD": ("intercambios", "evolucion-andorra"),
    "co2": ("generacion", "evolucion-renovable-no-renovable"),
}


async def _fetch(
    category: str,
    widget: str,
    start_date: str,
    end_date: str,
    time_trunc: str = "hour",
) -> dict[str, Any]:
    url = f"{REE_BASE_URL}/es/datos/{category}/{widget}"
    params: dict[str, str] = {
        "start_date": start_date,
        "end_date": end_date,
        "time_trunc": time_trunc,
    }

    cache_key = str(("ree", url, params))
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()

    cache.set(cache_key, data)
    return data


async def fetch_demand(
    start_date: str,
    end_date: str,
    kind: str = "real",
    time_trunc: str = "hour",
) -> dict[str, Any]:
    key = f"demand:{kind}"
    widget_key = _WIDGETS.get(key)
    if widget_key is None:
        raise ValueError(f"Unknown demand kind '{kind}'. Use 'real', 'forecast', or 'scheduled'.")
    return await _fetch(*widget_key, start_date, end_date, time_trunc)


async def fetch_generation_mix(
    start_date: str,
    end_date: str,
    time_trunc: str = "hour",
) -> dict[str, Any]:
    return await _fetch("generacion", "evolucion", start_date, end_date, time_trunc)


async def fetch_cross_border_flows(
    start_date: str,
    end_date: str,
    country: str | None = None,
    time_trunc: str = "hour",
) -> dict[str, Any]:
    if country:
        key = f"flows:{country.upper()}"
        widget_key = _WIDGETS.get(key)
        if widget_key is None:
            valid = [c for k in _WIDGETS if k.startswith("flows:") for c in [k.split(":")[1]]]
            raise ValueError(
                f"Unknown country '{country}'. Valid: {', '.join(sorted(valid))}."
            )
        return await _fetch(*widget_key, start_date, end_date, time_trunc)
    return await _fetch("intercambios", "evolucion", start_date, end_date, time_trunc)
