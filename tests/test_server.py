"""Smoke tests for the MCP server.

These verify the server can be imported and that every declared tool is
discoverable. Replace stub assertions with real fixture-based tests as the
clients get wired up.
"""
from __future__ import annotations

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


def test_stub_payload_shape():
    result = server.get_day_ahead_price(start="2026-05-20", end="2026-05-21")
    assert result["_stub"] is True
    assert result["tool"] == "get_day_ahead_price"
    assert result["received_params"]["start"] == "2026-05-20"
