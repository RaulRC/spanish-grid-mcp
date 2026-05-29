"""spanish-grid-mcp: MCP server exposing Spanish electricity grid data.

Tools are wired with stub implementations that return a placeholder payload
so the server starts and any MCP client can discover and call them. Replace
the stub bodies with real HTTP calls via `spanish_grid_mcp.clients.*`.

Run:
    python -m spanish_grid_mcp.server
"""
from __future__ import annotations

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("spanish-grid")


def _stub(tool: str, **params) -> dict:
    """Placeholder return used by every tool while wiring is being built out."""
    return {
        "_stub": True,
        "tool": tool,
        "received_params": params,
        "note": "Real data not wired yet. See src/spanish_grid_mcp/clients/*.py",
    }


# --- Prices (ESIOS) -------------------------------------------------------


@mcp.tool()
def get_day_ahead_price(start: str, end: str, granularity: str = "hour") -> dict:
    """Spanish day-ahead market prices (mercado diario), €/MWh.

    Args:
        start: Start date (ISO 8601, YYYY-MM-DD). Inclusive.
        end: End date (ISO 8601, YYYY-MM-DD). Exclusive.
        granularity: "hour" (default) or "day" (returns daily averages).
    """
    return _stub("get_day_ahead_price", start=start, end=end, granularity=granularity)


@mcp.tool()
def get_pvpc_price(start: str, end: str, tariff: str = "2.0TD") -> dict:
    """PVPC regulated household tariff prices, €/MWh per hour.

    PVPC (Precio Voluntario para el Pequeño Consumidor) is the regulated
    Spanish household electricity tariff. Only defined from 2014-04-01 onwards.

    Args:
        start: Start date (ISO 8601, YYYY-MM-DD).
        end: End date (ISO 8601, YYYY-MM-DD).
        tariff: Tariff code. Currently only "2.0TD" is supported (the default
            since 2021-06-01).
    """
    return _stub("get_pvpc_price", start=start, end=end, tariff=tariff)


# --- Demand & generation (REE / ESIOS) ------------------------------------


@mcp.tool()
def get_demand(start: str, end: str, kind: str = "real") -> dict:
    """Spanish electricity demand, MW.

    Args:
        start: Start date (ISO 8601).
        end: End date (ISO 8601).
        kind: One of "real" (actual), "forecast" (day-ahead), or "scheduled".
    """
    return _stub("get_demand", start=start, end=end, kind=kind)


@mcp.tool()
def get_generation_mix(start: str, end: str, granularity: str = "hour") -> dict:
    """Spanish generation by technology, MW per technology.

    Returns a breakdown across nuclear, coal, combined cycle (gas), wind,
    solar PV, solar thermal, hydro, cogeneration, and other.

    Args:
        start: Start date (ISO 8601).
        end: End date (ISO 8601).
        granularity: "hour" (default) or "day".
    """
    return _stub("get_generation_mix", start=start, end=end, granularity=granularity)


@mcp.tool()
def get_cross_border_flows(start: str, end: str, country: str | None = None) -> dict:
    """Spanish electricity interconnections (imports/exports), MW.

    Spain has cross-border lines to France, Portugal, Morocco, and Andorra.
    Positive = export, negative = import (from Spain's perspective).

    Args:
        start: Start date (ISO 8601).
        end: End date (ISO 8601).
        country: Optional filter — "FR", "PT", "MA", or "AD". If omitted,
            returns all borders.
    """
    return _stub("get_cross_border_flows", start=start, end=end, country=country)


@mcp.tool()
def get_co2_intensity(start: str, end: str) -> dict:
    """Grid CO₂ intensity for the Spanish system, gCO₂/kWh, hourly.

    Args:
        start: Start date (ISO 8601).
        end: End date (ISO 8601).
    """
    return _stub("get_co2_intensity", start=start, end=end)


# --- Weather (AEMET) ------------------------------------------------------


@mcp.tool()
def list_weather_stations(region: str | None = None) -> dict:
    """List AEMET weather stations, optionally filtered by region.

    Returns station IDs (use with get_weather_observations), names, provinces,
    and coordinates.

    Args:
        region: Optional ISO autonomous community code (e.g. "MD" for Madrid,
            "AN" for Andalucía). Omit for all stations.
    """
    return _stub("list_weather_stations", region=region)


@mcp.tool()
def get_weather_observations(station_id: str, start: str, end: str) -> dict:
    """Hourly weather observations from one AEMET station.

    Returns temperature (°C), wind speed (km/h), wind direction (°),
    precipitation (mm), and solar irradiance where available.

    Args:
        station_id: AEMET station code (see list_weather_stations).
        start: Start date (ISO 8601).
        end: End date (ISO 8601). Max range per call: 31 days.
    """
    return _stub(
        "get_weather_observations", station_id=station_id, start=start, end=end
    )


# --- Discovery / escape hatch (ESIOS) -------------------------------------


@mcp.tool()
def search_esios_indicators(query: str, limit: int = 10) -> dict:
    """Free-text search across the ~2000 ESIOS indicators.

    Use this when the wrapped tools above don't cover what you need. Returns
    candidate indicator IDs and descriptions; feed the chosen ID to
    get_esios_indicator.

    Args:
        query: Spanish or English search terms (e.g. "interconexión Francia").
        limit: Max results to return. Default 10.
    """
    return _stub("search_esios_indicators", query=query, limit=limit)


@mcp.tool()
def get_esios_indicator(indicator_id: int, start: str, end: str) -> dict:
    """Raw access to any ESIOS indicator by numeric ID.

    Escape hatch for indicators not wrapped above. Use search_esios_indicators
    first to find the right ID.

    Args:
        indicator_id: Numeric indicator ID from ESIOS.
        start: Start date (ISO 8601).
        end: End date (ISO 8601).
    """
    return _stub(
        "get_esios_indicator", indicator_id=indicator_id, start=start, end=end
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
