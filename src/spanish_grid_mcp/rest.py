"""spanish-grid-rest: REST API for Spanish electricity grid data.

Data sources: ESIOS (prices, indicators), REE apidatos (demand, generation,
flows), AEMET OpenData (weather).

Run:
    python -m spanish_grid_mcp.rest
    # or
    uvicorn spanish_grid_mcp.rest:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

_dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_dotenv_path)

from spanish_grid_mcp.clients import aemet, esios, ree  # noqa: E402

app = FastAPI(
    title="spanish-grid REST API",
    description="Spanish electricity grid data — prices, demand, generation, CO₂, weather.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health -----------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok"}


# --- Prices (ESIOS) ---------------------------------------------------------


@app.get("/api/day-ahead-price")
async def get_day_ahead_price(
    start: str = Query(..., description="Start date (ISO 8601)"),
    end: str = Query(..., description="End date (ISO 8601, exclusive)"),
    granularity: str = Query("hour", description="hour or day"),
):
    if not esios.is_configured():
        raise HTTPException(status_code=503, detail="ESIOS_TOKEN not configured")
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


@app.get("/api/pvpc-price")
async def get_pvpc_price(
    start: str = Query(..., description="Start date (ISO 8601)"),
    end: str = Query(..., description="End date (ISO 8601)"),
    tariff: str = Query("2.0TD", description="Tariff code"),
):
    if not esios.is_configured():
        raise HTTPException(status_code=503, detail="ESIOS_TOKEN not configured")
    indicator_id = {"2.0TD": 1001}.get(tariff)
    if indicator_id is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported tariff '{tariff}'. Currently only '2.0TD' is supported.",
        )
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


# --- Demand & generation (REE) ----------------------------------------------


@app.get("/api/demand")
async def get_demand(
    start: str = Query(..., description="Start date (ISO 8601)"),
    end: str = Query(..., description="End date (ISO 8601)"),
):
    data = await ree.fetch_demand(start_date=start, end_date=end)
    return {"unit": "MW", "data": data.get("included", [])}


@app.get("/api/generation-mix")
async def get_generation_mix(
    start: str = Query(..., description="Start date (ISO 8601)"),
    end: str = Query(..., description="End date (ISO 8601)"),
    granularity: str = Query("day", description="day or hour"),
):
    data = await ree.fetch_generation_mix(
        start_date=start, end_date=end, time_trunc=granularity
    )
    return {"granularity": granularity, "unit": "MW", "data": data.get("included", [])}


@app.get("/api/cross-border-flows")
async def get_cross_border_flows(
    start: str = Query(..., description="Start date (ISO 8601)"),
    end: str = Query(..., description="End date (ISO 8601)"),
):
    data = await ree.fetch_demand(start_date=start, end_date=end)
    return {"unit": "MW", "data": data.get("included", [])}


@app.get("/api/co2-intensity")
async def get_co2_intensity(
    start: str = Query(..., description="Start date (ISO 8601)"),
    end: str = Query(..., description="End date (ISO 8601)"),
):
    return await ree.compute_co2_intensity(start_date=start, end_date=end)


# --- Weather (AEMET) --------------------------------------------------------


@app.get("/api/weather-stations")
async def list_weather_stations(
    region: str | None = Query(None, description="ISO autonomous community code (e.g. MD)"),
):
    if not aemet.is_configured():
        raise HTTPException(status_code=503, detail="AEMET_TOKEN not configured")
    stations = await aemet.list_stations(region=region)
    return {"region": region, "stations": stations}


@app.get("/api/weather-observations")
async def get_weather_observations(
    station_id: str = Query(..., description="AEMET station code"),
    start: str = Query(..., description="Start date (ISO 8601)"),
    end: str = Query(..., description="End date (ISO 8601, max 31-day range)"),
):
    if not aemet.is_configured():
        raise HTTPException(status_code=503, detail="AEMET_TOKEN not configured")
    observations = await aemet.fetch_observations(
        station_id=station_id, start_date=start, end_date=end
    )
    return {"station_id": station_id, "observations": observations}


# --- ESIOS discovery / escape hatch -----------------------------------------


@app.get("/api/esios/search")
async def search_esios_indicators(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Max results"),
):
    if not esios.is_configured():
        raise HTTPException(status_code=503, detail="ESIOS_TOKEN not configured")
    data = await esios.search_indicators(query=q, limit=limit)
    return {"query": q, "limit": limit, "results": data.get("indicators", [])}


@app.get("/api/esios/indicator/{indicator_id}")
async def get_esios_indicator(
    indicator_id: int,
    start: str = Query(..., description="Start date (ISO 8601)"),
    end: str = Query(..., description="End date (ISO 8601)"),
):
    if not esios.is_configured():
        raise HTTPException(status_code=503, detail="ESIOS_TOKEN not configured")
    return await esios.fetch_indicator(
        indicator_id=indicator_id,
        start_date=start,
        end_date=end,
    )


# --- CLI entrypoint ---------------------------------------------------------


def main() -> None:
    import uvicorn

    uvicorn.run("spanish_grid_mcp.rest:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
