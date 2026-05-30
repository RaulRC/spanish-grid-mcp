"""Tests for the MCP server tool definitions.

Uses mocking to verify each tool handles config checks, errors, and data
formatting correctly without hitting real APIs.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from spanish_grid_mcp import server


EXPECTED_TOOLS = {
    "get_day_ahead_price",
    "get_pvpc_price",
    "get_demand",
    "get_generation_mix",
    "get_cross_border_flows",
    "get_co2_intensity",
    "list_weather_stations",
    "get_weather_observations",
    "search_esios_indicators",
    "get_esios_indicator",
}


@pytest.mark.asyncio
async def test_all_tools_registered():
    tools = await server.mcp.list_tools()
    names = {t.name for t in tools}
    assert names == EXPECTED_TOOLS, f"Missing: {EXPECTED_TOOLS - names}, extra: {names - EXPECTED_TOOLS}"


# --- ESIOS tools ---


@pytest.mark.asyncio
async def test_get_day_ahead_price_unconfigured():
    with patch("spanish_grid_mcp.server.esios.is_configured", return_value=False):
        result = await server.get_day_ahead_price(start="2026-05-28", end="2026-05-29")
    assert "error" in result
    assert "ESIOS_TOKEN" in result["error"]


@pytest.mark.asyncio
async def test_get_day_ahead_price_configured():
    mock_data = {"indicator": {"name": "Precio mercado diario", "values": [{"value": 50.0}]}}
    with (
        patch("spanish_grid_mcp.server.esios.is_configured", return_value=True),
        patch("spanish_grid_mcp.server.esios.fetch_indicator", AsyncMock(return_value=mock_data)),
    ):
        result = await server.get_day_ahead_price(start="2026-05-28", end="2026-05-29")
    assert result["indicator_id"] == 600
    assert result["unit"] == "€/MWh"
    assert result["values"] == [{"value": 50.0}]


@pytest.mark.asyncio
async def test_get_pvpc_price_unconfigured():
    with patch("spanish_grid_mcp.server.esios.is_configured", return_value=False):
        result = await server.get_pvpc_price(start="2026-05-28", end="2026-05-29")
    assert "error" in result


@pytest.mark.asyncio
async def test_get_pvpc_price_unknown_tariff():
    with patch("spanish_grid_mcp.server.esios.is_configured", return_value=True):
        result = await server.get_pvpc_price(start="2026-05-28", end="2026-05-29", tariff="3.0A")
    assert "error" in result
    assert "Unsupported tariff" in result["error"]


@pytest.mark.asyncio
async def test_search_esios_indicators_unconfigured():
    with patch("spanish_grid_mcp.server.esios.is_configured", return_value=False):
        result = await server.search_esios_indicators(query="solar")
    assert "error" in result


@pytest.mark.asyncio
async def test_get_esios_indicator_unconfigured():
    with patch("spanish_grid_mcp.server.esios.is_configured", return_value=False):
        result = await server.get_esios_indicator(indicator_id=600, start="2026-05-28", end="2026-05-29")
    assert "error" in result


# --- REE tools ---


@pytest.mark.asyncio
async def test_get_demand():
    mock_data = {"included": [{"id": "10297", "attributes": {"values": [{"value": 28000}]}}]}
    with patch("spanish_grid_mcp.server.ree.fetch_demand", AsyncMock(return_value=mock_data)):
        result = await server.get_demand(start="2025-06-01", end="2025-06-02")
    assert result["unit"] == "MW"
    assert len(result["data"]) == 1


@pytest.mark.asyncio
async def test_get_generation_mix():
    mock_data = {"included": [{"attributes": {"title": "Nuclear", "values": [{"value": 5000}]}}]}
    with patch("spanish_grid_mcp.server.ree.fetch_generation_mix", AsyncMock(return_value=mock_data)):
        result = await server.get_generation_mix(start="2025-06-01", end="2025-06-02")
    assert result["granularity"] == "day"
    assert len(result["data"]) == 1


@pytest.mark.asyncio
async def test_get_co2_intensity():
    mock_data = {"gco2_per_kwh": 250.0, "total_co2_kg": 100000.0, "total_mwh": 400.0, "breakdown": []}
    with patch("spanish_grid_mcp.server.ree.compute_co2_intensity", AsyncMock(return_value=mock_data)):
        result = await server.get_co2_intensity(start="2025-06-01", end="2025-06-02")
    assert result["gco2_per_kwh"] == 250.0


# --- AEMET tools ---


@pytest.mark.asyncio
async def test_list_weather_stations_unconfigured():
    with patch("spanish_grid_mcp.server.aemet.is_configured", return_value=False):
        result = await server.list_weather_stations()
    assert "error" in result
    assert "AEMET_TOKEN" in result["error"]


@pytest.mark.asyncio
async def test_get_weather_observations_unconfigured():
    with patch("spanish_grid_mcp.server.aemet.is_configured", return_value=False):
        result = await server.get_weather_observations(station_id="1234X", start="2026-05-28", end="2026-05-29")
    assert "error" in result
    assert "AEMET_TOKEN" in result["error"]
