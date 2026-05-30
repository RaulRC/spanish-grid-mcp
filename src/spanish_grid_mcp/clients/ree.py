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

# Standard emission factors in gCO₂/kWh per generation type
_EMISSION_FACTORS: dict[str, float] = {
    "Nuclear": 12,
    "Carbón": 820,
    "Lignito": 820,
    "Ciclo combinado": 490,
    "Fuel + Gas": 490,
    "Motores diésel": 700,
    "Turbina de gas": 700,
    "Turbina de vapor": 700,
    "Cogeneración": 400,
    "Hidráulica": 24,
    "Hidroeólica": 24,
    "Eólica": 11,
    "Solar fotovoltaica": 41,
    "Solar térmica": 27,
    "Otras renovables": 50,
    "Residuos no renovables": 600,
    "Residuos renovables": 200,
}


def _fmt_date(d: str) -> str:
    """Append T00:00:00 if the date is bare YYYY-MM-DD."""
    if "T" not in d:
        return f"{d}T00:00:00"
    return d


async def _fetch(
    category: str,
    widget: str,
    start_date: str,
    end_date: str,
    time_trunc: str = "day",
) -> dict[str, Any]:
    url = f"{REE_BASE_URL}/es/datos/{category}/{widget}"
    params: dict[str, str] = {
        "start_date": _fmt_date(start_date),
        "end_date": _fmt_date(end_date),
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
    time_trunc: str = "day",
) -> dict[str, Any]:
    return await _fetch("demanda", "evolucion", start_date, end_date, time_trunc)


async def fetch_generation_mix(
    start_date: str,
    end_date: str,
    time_trunc: str = "day",
) -> dict[str, Any]:
    return await _fetch("generacion", "estructura-generacion", start_date, end_date, time_trunc)


async def compute_co2_intensity(
    start_date: str,
    end_date: str,
    time_trunc: str = "day",
) -> dict[str, Any]:
    data = await fetch_generation_mix(start_date, end_date, time_trunc)
    included = data.get("included", [])

    total_mwh = 0.0
    total_co2 = 0.0
    breakdown: list[dict[str, Any]] = []

    for item in included:
        attrs = item.get("attributes", {})
        title = attrs.get("title", "")
        values = attrs.get("values", [])
        factor = _EMISSION_FACTORS.get(title, 0)

        for v in values:
            mwh = v.get("value", 0)
            if isinstance(mwh, (int, float)):
                total_mwh += mwh
                total_co2 += mwh * factor
                breakdown.append({
                    "type": title,
                    "mwh": mwh,
                    "emission_factor": factor,
                    "co2_kg": mwh * factor,
                })

    intensity = round(total_co2 / total_mwh, 1) if total_mwh > 0 else 0
    return {
        "gco2_per_kwh": intensity,
        "total_co2_kg": round(total_co2, 1),
        "total_mwh": round(total_mwh, 1),
        "breakdown": breakdown,
    }
