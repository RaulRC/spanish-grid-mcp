"""Unit tests for the HTTP client modules.

All HTTP calls are mocked so tests run without network access or real tokens.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from spanish_grid_mcp.clients import aemet, esios, ree


# --- ESIOS client ---


@pytest.mark.asyncio
async def test_esios_is_configured():
    with patch("spanish_grid_mcp.clients.esios.ESIOS_TOKEN", "real-token"):
        assert esios.is_configured() is True
    with patch("spanish_grid_mcp.clients.esios.ESIOS_TOKEN", ""):
        assert esios.is_configured() is False


@pytest.mark.asyncio
async def test_esios_fetch_indicator():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.json.return_value = {"indicator": {"id": 600, "values": []}}

    async def mock_get(*args, **kwargs):
        return mock_resp

    with (
        patch("spanish_grid_mcp.clients.esios.ESIOS_TOKEN", "token"),
        patch("spanish_grid_mcp.cache.cache.get", return_value=None),
        patch("spanish_grid_mcp.cache.cache.set"),
        patch("httpx.AsyncClient.get", mock_get),
    ):
        data = await esios.fetch_indicator(600, "2026-05-20", "2026-05-21")
    assert data["indicator"]["id"] == 600


@pytest.mark.asyncio
async def test_esios_fetch_indicator_cached():
    expected = {"indicator": {"id": 600, "values": [{"value": 55.0}]}}
    with (
        patch("spanish_grid_mcp.cache.cache.get", return_value=expected),
        patch("httpx.AsyncClient.get") as mock_get,
    ):
        data = await esios.fetch_indicator(600, "2026-05-20", "2026-05-21")
    assert data["indicator"]["values"][0]["value"] == 55.0
    mock_get.assert_not_called()


# --- REE client ---





@pytest.mark.asyncio
async def test_ree_fetch_demand():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.json.return_value = {"data": {"values": [{"value": 30000}]}}

    async def mock_get(*args, **kwargs):
        return mock_resp

    with (
        patch("spanish_grid_mcp.cache.cache.get", return_value=None),
        patch("spanish_grid_mcp.cache.cache.set"),
        patch("httpx.AsyncClient.get", mock_get),
    ):
        data = await ree.fetch_demand("2026-05-20", "2026-05-21", kind="real")
    assert data["data"]["values"][0]["value"] == 30000


@pytest.mark.asyncio
async def test_ree_fetch_demand_invalid_kind():
    with pytest.raises(ValueError, match="Unknown demand kind"):
        await ree.fetch_demand("2026-05-20", "2026-05-21", kind="invalid")


@pytest.mark.asyncio
async def test_ree_fetch_generation_mix():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.json.return_value = {"data": {"values": [{"nuclear": 5000, "wind": 8000}]}}

    async def mock_get(*args, **kwargs):
        return mock_resp

    with (
        patch("spanish_grid_mcp.cache.cache.get", return_value=None),
        patch("spanish_grid_mcp.cache.cache.set"),
        patch("httpx.AsyncClient.get", mock_get),
    ):
        data = await ree.fetch_generation_mix("2026-05-20", "2026-05-21")
    assert data["data"]["values"][0]["nuclear"] == 5000


@pytest.mark.asyncio
async def test_ree_fetch_cross_border_flows_invalid_country():
    with pytest.raises(ValueError, match="Unknown country"):
        await ree.fetch_cross_border_flows("2026-05-20", "2026-05-21", country="XX")


# --- AEMET client ---


@pytest.mark.asyncio
async def test_aemet_is_configured():
    with patch("spanish_grid_mcp.clients.aemet.AEMET_TOKEN", "real-token"):
        assert aemet.is_configured() is True
    with patch("spanish_grid_mcp.clients.aemet.AEMET_TOKEN", ""):
        assert aemet.is_configured() is False


@pytest.mark.asyncio
async def test_aemet_list_stations():
    step1_resp = MagicMock(spec=httpx.Response)
    step1_resp.json.return_value = {
        "estado": 200,
        "datos": "https://opendata.aemet.es/data/stations.json",
    }
    step2_resp = MagicMock(spec=httpx.Response)
    step2_resp.json.return_value = [
        {"id": "1234X", "nombre": "Madrid Retiro", "provincia": "Madrid"},
    ]

    responses = iter([step1_resp, step2_resp])

    async def mock_get(*args, **kwargs):
        return next(responses)

    with (
        patch("spanish_grid_mcp.cache.cache.get", return_value=None),
        patch("spanish_grid_mcp.cache.cache.set"),
        patch("spanish_grid_mcp.clients.aemet.AEMET_TOKEN", "token"),
        patch("httpx.AsyncClient.get", mock_get),
    ):
        stations = await aemet.list_stations()
    assert len(stations) == 1
    assert stations[0]["id"] == "1234X"


@pytest.mark.asyncio
async def test_aemet_api_error():
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = {"estado": 404, "descripcion": "Recurso no encontrado"}

    async def mock_get(*args, **kwargs):
        return resp

    with (
        patch("spanish_grid_mcp.cache.cache.get", return_value=None),
        patch("spanish_grid_mcp.clients.aemet.AEMET_TOKEN", "token"),
        patch("httpx.AsyncClient.get", mock_get),
    ):
        with pytest.raises(RuntimeError, match="AEMET API error"):
            await aemet.list_stations()


@pytest.mark.asyncio
async def test_aemet_missing_datos_url():
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = {"estado": 200, "datos": ""}

    async def mock_get(*args, **kwargs):
        return resp

    with (
        patch("spanish_grid_mcp.cache.cache.get", return_value=None),
        patch("spanish_grid_mcp.clients.aemet.AEMET_TOKEN", "token"),
        patch("httpx.AsyncClient.get", mock_get),
    ):
        with pytest.raises(RuntimeError, match="missing 'datos' URL"):
            await aemet.list_stations()
