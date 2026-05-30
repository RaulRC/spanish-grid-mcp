"""spanish-grid-mcp: MCP server exposing Spanish electricity grid data.

Data sources: ESIOS (prices, indicators), REE apidatos (demand, generation,
flows), AEMET OpenData (weather).

Run:
    python -m spanish_grid_mcp.server
"""
from __future__ import annotations

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from spanish_grid_mcp.clients import aemet, esios, ree

load_dotenv()

mcp = FastMCP("spanish-grid")


# --- Prices (ESIOS) -------------------------------------------------------


@mcp.tool()
async def get_day_ahead_price(start: str, end: str, granularity: str = "hour") -> dict:
    """Spanish day-ahead market prices (mercado diario), €/MWh.

    Args:
        start: Start date (ISO 8601, YYYY-MM-DD). Inclusive.
        end: End date (ISO 8601, YYYY-MM-DD). Exclusive.
        granularity: "hour" (default) or "day" (returns daily averages).
    """
    if not esios.is_configured():
        return {"error": "ESIOS_TOKEN not configured"}

    time_trunc_map = {"hour": "hour", "day": "day"}
    data = await esios.fetch_indicator(
        indicator_id=600,
        start_date=start,
        end_date=end,
        time_trunc=time_trunc_map.get(granularity),
    )
    indicator = data.get("indicator", {})
    return {
        "indicator": indicator.get("name", ""),
        "indicator_id": 600,
        "unit": "€/MWh",
        "granularity": granularity,
        "values": indicator.get("values", []),
    }


@mcp.tool()
async def get_pvpc_price(start: str, end: str, tariff: str = "2.0TD") -> dict:
    """PVPC regulated household tariff prices, €/MWh per hour.

    PVPC (Precio Voluntario para el Pequeño Consumidor) is the regulated
    Spanish household electricity tariff. Only defined from 2014-04-01 onwards.

    Args:
        start: Start date (ISO 8601, YYYY-MM-DD).
        end: End date (ISO 8601, YYYY-MM-DD).
        tariff: Tariff code. Currently only "2.0TD" is supported (the default
            since 2021-06-01).
    """
    if not esios.is_configured():
        return {"error": "ESIOS_TOKEN not configured"}

    indicator_id = {"2.0TD": 1001}.get(tariff)
    if indicator_id is None:
        return {
            "error": f"Unsupported tariff '{tariff}'. Currently only '2.0TD' is supported."
        }

    data = await esios.fetch_indicator(
        indicator_id=indicator_id,
        start_date=start,
        end_date=end,
        time_trunc="hour",
    )
    indicator = data.get("indicator", {})
    return {
        "indicator": indicator.get("name", ""),
        "indicator_id": indicator_id,
        "unit": "€/MWh",
        "tariff": tariff,
        "values": indicator.get("values", []),
    }


# --- Demand & generation (REE / ESIOS) ------------------------------------


@mcp.tool()
async def get_demand(start: str, end: str, kind: str = "real") -> dict:
    """Spanish electricity demand, MW.

    Args:
        start: Start date (ISO 8601).
        end: End date (ISO 8601).
        kind: One of "real" (actual), "forecast" (day-ahead), or "scheduled".
    """
    try:
        data = await ree.fetch_demand(start_date=start, end_date=end, kind=kind)
        return {"kind": kind, "data": data.get("data", {}).get("values", []), "unit": "MW"}
    except ValueError as e:
        return {"error": str(e)}


@mcp.tool()
async def get_generation_mix(start: str, end: str, granularity: str = "hour") -> dict:
    """Spanish generation by technology, MW per technology.

    Returns a breakdown across nuclear, coal, combined cycle (gas), wind,
    solar PV, solar thermal, hydro, cogeneration, and other.

    Args:
        start: Start date (ISO 8601).
        end: End date (ISO 8601).
        granularity: "hour" (default) or "day".
    """
    data = await ree.fetch_generation_mix(start_date=start, end_date=end, time_trunc=granularity)
    return {"granularity": granularity, "unit": "MW", "data": data.get("data", {}).get("values", [])}


@mcp.tool()
async def get_cross_border_flows(start: str, end: str, country: str | None = None) -> dict:
    """Spanish electricity interconnections (imports/exports), MW.

    Spain has cross-border lines to France, Portugal, Morocco, and Andorra.
    Positive = export, negative = import (from Spain's perspective).

    Args:
        start: Start date (ISO 8601).
        end: End date (ISO 8601).
        country: Optional filter — "FR", "PT", "MA", or "AD". If omitted,
            returns all borders.
    """
    try:
        data = await ree.fetch_cross_border_flows(start_date=start, end_date=end, country=country)
        return {"country": country, "unit": "MW", "data": data.get("data", {}).get("values", [])}
    except ValueError as e:
        return {"error": str(e)}


@mcp.tool()
async def get_co2_intensity(start: str, end: str) -> dict:
    """Grid CO₂ intensity for the Spanish system, gCO₂/kWh, hourly.

    Args:
        start: Start date (ISO 8601).
        end: End date (ISO 8601).
    """
    if not esios.is_configured():
        return {"error": "ESIOS_TOKEN not configured"}

    data = await esios.fetch_indicator(indicator_id=739, start_date=start, end_date=end)
    indicator = data.get("indicator", {})
    return {
        "indicator": indicator.get("name", ""),
        "indicator_id": 739,
        "unit": "gCO₂/kWh",
        "values": indicator.get("values", []),
    }


# --- Weather (AEMET) ------------------------------------------------------


@mcp.tool()
async def list_weather_stations(region: str | None = None) -> dict:
    """List AEMET weather stations, optionally filtered by region.

    Returns station IDs (use with get_weather_observations), names, provinces,
    and coordinates.

    Args:
        region: Optional ISO autonomous community code (e.g. "MD" for Madrid,
            "AN" for Andalucía). Omit for all stations.
    """
    if not aemet.is_configured():
        return {"error": "AEMET_TOKEN not configured"}
    stations = await aemet.list_stations(region=region)
    return {"region": region, "stations": stations}


@mcp.tool()
async def get_weather_observations(station_id: str, start: str, end: str) -> dict:
    """Hourly weather observations from one AEMET station.

    Returns temperature (°C), wind speed (km/h), wind direction (°),
    precipitation (mm), and solar irradiance where available.

    Args:
        station_id: AEMET station code (see list_weather_stations).
        start: Start date (ISO 8601).
        end: End date (ISO 8601). Max range per call: 31 days.
    """
    if not aemet.is_configured():
        return {"error": "AEMET_TOKEN not configured"}
    observations = await aemet.fetch_observations(station_id=station_id, start_date=start, end_date=end)
    return {"station_id": station_id, "observations": observations}


# --- Discovery / escape hatch (ESIOS) -------------------------------------


@mcp.tool()
async def search_esios_indicators(query: str, limit: int = 10) -> dict:
    """Free-text search across the ~2000 ESIOS indicators.

    Use this when the wrapped tools above don't cover what you need. Returns
    candidate indicator IDs and descriptions; feed the chosen ID to
    get_esios_indicator.

    Args:
        query: Spanish or English search terms (e.g. "interconexión Francia").
        limit: Max results to return. Default 10.
    """
    if not esios.is_configured():
        return {"error": "ESIOS_TOKEN not configured"}

    data = await esios.search_indicators(query=query, limit=limit)
    return {
        "query": query,
        "limit": limit,
        "results": data.get("indicators", []),
    }


@mcp.tool()
async def get_esios_indicator(indicator_id: int, start: str, end: str) -> dict:
    """Raw access to any ESIOS indicator by numeric ID.

    Escape hatch for indicators not wrapped above. Use search_esios_indicators
    first to find the right ID.

    Args:
        indicator_id: Numeric indicator ID from ESIOS.
        start: Start date (ISO 8601).
        end: End date (ISO 8601).
    """
    if not esios.is_configured():
        return {"error": "ESIOS_TOKEN not configured"}

    data = await esios.fetch_indicator(
        indicator_id=indicator_id,
        start_date=start,
        end_date=end,
    )
    return data


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
