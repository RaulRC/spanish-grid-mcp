# spanish-grid-mcp

**Alpha** — Spanish electricity grid data, served as MCP tools *(for LLM
agents)* and as a REST API *(for everything else)*.

```json
// MCP:  "What was the average price yesterday?"
// REST: curl http://localhost:8000/api/day-ahead-price?start=...&end=...
```

### Data sources

| Source | Auth | Coverage |
|--------|------|----------|
| [ESIOS](https://api.esios.ree.es) (Red Eléctrica) | `ESIOS_TOKEN` (free, email `consultasios@ree.es`) | ~2000 grid indicators — day-ahead prices, PVPC, hourly values |
| [REE apidatos](https://apidatos.ree.es) | None | Demand, generation mix, CO₂ intensity |
| [AEMET OpenData](https://opendata.aemet.es/opendata/api) | `AEMET_TOKEN` (free, [register here](https://opendata.aemet.es/centrodedescargas/altaUsuario)) | Station inventory, hourly weather observations |

---

## Quick start

```bash
pip install spanish-grid-mcp

cp .env.example .env
# fill in ESIOS_TOKEN and AEMET_TOKEN

python -m spanish_grid_mcp.server
```

The server speaks MCP over stdio. With no client attached it sits waiting for
JSON-RPC — that's expected. Ctrl-C to exit.

---

## Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "spanish-grid": {
      "command": "python",
      "args": ["-m", "spanish_grid_mcp.server"],
      "env": {
        "ESIOS_TOKEN": "your-token",
        "AEMET_TOKEN": "your-token"
      }
    }
  }
}
```

### opencode

Add to `~/.config/opencode/opencode.jsonc`:

```json
{
  "mcp": {
    "spanish-grid": {
      "type": "local",
      "command": ["python", "-m", "spanish_grid_mcp.server"],
      "enabled": true,
      "env": {
        "ESIOS_TOKEN": "your-token",
        "AEMET_TOKEN": "your-token"
      }
    }
  }
}
```

### Any MCP client

Point it at `python -m spanish_grid_mcp.server` with the two env vars set.

---

## REST API

The same data is also available as a FastAPI REST server with auto-generated
docs at **`http://localhost:8000/docs`**.

```bash
pip install spanish-grid-mcp

python -m spanish_grid_mcp.rest
# → uvicorn running on http://127.0.0.1:8000

# production
uvicorn spanish_grid_mcp.rest:app --host 0.0.0.0 --port 8000
```

### Endpoints

All `GET` requests, all return JSON.

| Endpoint | Parameters | Description |
|---|---|---|
| `/health` | — | Health check |
| `/api/day-ahead-price` | `start`, `end`, `granularity` | Day-ahead market prices, €/MWh |
| `/api/pvpc-price` | `start`, `end`, `tariff` | PVPC regulated tariff, €/MWh |
| `/api/demand` | `start`, `end` | Electricity demand, MW |
| `/api/generation-mix` | `start`, `end`, `granularity` | Generation by technology, MW |
| `/api/cross-border-flows` | `start`, `end` | International exchange balance, MW |
| `/api/co2-intensity` | `start`, `end` | CO₂ intensity, gCO₂/kWh |
| `/api/weather-stations` | `region` (optional) | AEMET station inventory |
| `/api/weather-observations` | `station_id`, `start`, `end` | Hourly weather observations |
| `/api/esios/search` | `q`, `limit` | Search ESIOS indicators |
| `/api/esios/indicator/{id}` | `start`, `end` | Raw ESIOS indicator |

```bash
# Examples
curl "http://localhost:8000/api/demand?start=2025-06-01&end=2025-06-02"
curl "http://localhost:8000/api/co2-intensity?start=2025-06-01&end=2025-06-02"
curl "http://localhost:8000/api/weather-stations?region=MD"
```

---

## Tools

| Tool | Data source | Granularity | Description |
|------|-------------|-------------|-------------|
| `get_day_ahead_price` | ESIOS | hour / day | Spanish day-ahead market prices, €/MWh |
| `get_pvpc_price` | ESIOS | hour | PVPC regulated household tariff, €/MWh (tariff `2.0TD` since 2021) |
| `search_esios_indicators` | ESIOS | — | Free-text search across ~2000 ESIOS indicators |
| `get_esios_indicator` | ESIOS | varies | Raw access to any ESIOS indicator by numeric ID |
| `get_demand` | REE | day | Spanish electricity demand, MW |
| `get_generation_mix` | REE | day (hour via ESIOS) | Generation by technology (wind, solar, nuclear, gas…), MW |
| `get_co2_intensity` | REE | day | Grid CO₂ intensity computed from generation mix + emission factors, gCO₂/kWh |
| `get_cross_border_flows` | REE | day | International exchange balance from demand data, MW |
| `list_weather_stations` | AEMET | — | Station inventory (ID, name, province, coordinates), optionally filtered by autonomous community |
| `get_weather_observations` | AEMET | hour | Temperature, wind, precipitation, pressure (max 31-day range per call) |

> **Note on granularity:** REE apidatos rejects `time_trunc=hour` for historical
> queries — daily is the default. Hourly generation is available via ESIOS
> indicators (e.g. indicator 600 for price, or `get_esios_indicator` for
> hourly generation breakdowns).

---

## Docker

```bash
# build and run
docker compose up -d

# or build manually
docker build -t spanish-grid-mcp .
docker run -d --env-file .env -p 8000:8000 spanish-grid-mcp

# verify
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

The container runs the REST API on port 8000. Cache is persisted in a named
volume (`spanish-grid-cache`). Supply tokens via `.env` or individual env vars.

---

## Architecture

```
server.py  ← FastMCP app, 10 MCP tools, main()         [MCP over stdio]
rest.py    ← FastAPI app, 11 routes, auto OpenAPI docs  [REST over HTTP]

  ├─ clients/esios.py  →  api.esios.ree.es  (x-api-key auth)
  ├─ clients/ree.py    →  apidatos.ree.es    (no auth)
  └─ clients/aemet.py  →  opendata.aemet.es  (api_key query param)
         │
         └─ two-step fetch pattern:
            1. GET /api/{endpoint}?api_key=…  →  returns {"datos": "https://…"}
            2. GET https://…                  →  actual payload (ISO-8859-15 encoded)
```

- **Caching:** `diskcache.Cache` at `~/.cache/spanish-grid-mcp` (override via
  `SPANISH_GRID_CACHE_DIR`). Cache key = URL + query params.
- **CO₂ intensity:** Computed from the REE generation mix using standard
  emission factors per technology (gCO₂/kWh). [See source](src/spanish_grid_mcp/clients/ree.py).
- **AEMET encoding:** Responses are ISO-8859-15 — decoded via
  `resp.content.decode(charset)` rather than `resp.json()`.
- **Dotenv:** Loaded automatically on import — no manual `load_dotenv()` needed.
- **Dual protocol:** Both `server.py` and `rest.py` share the same client
  modules — data logic is not duplicated.

---

## Development

```bash
pip install -e ".[dev]"

# run tests
pytest

# run a single test
pytest tests/test_server.py::test_all_tools_registered -v

# lint
ruff check

# lint + fix
ruff check --fix
```

All tests use `pytest-asyncio` and mock HTTP calls. CI runs on push/PR
(Python 3.10–3.12, ruff check + pytest).

---

## Future work

- **Per-border cross-border flows** — The REE `intercambios/evolucion-{pais}`
  endpoints return 500 errors. Awaiting API fix to split France, Portugal,
  Morocco, and Andorra flows.
- **Rate limiting & retry** — Add exponential backoff to HTTP clients,
  respecting any upstream rate limits.
- **Better AEMET error messages** — Surface AEMET API error descriptions
  instead of generic httpx exceptions on the second-step fetch.
- **Hourly generation via ESIOS** — Wrap the relevant ESIOS indicators so
  users can get generation mix at hourly granularity without using the raw
  `get_esios_indicator` escape hatch.
- **CLI one-shot mode** — Let users run `spanish-grid-mcp get_demand
  2025-06-01 2025-06-02` as a standalone CLI command without an MCP client.
  (Partially covered by the REST API — `curl` is the one-shot tool.)
- **Solar irradiance in kWh/m²** — Normalise AEMET solar radiation data to
  standard energy units.
- **Integration tests** — Scheduled tests that exercise the real APIs (with
  tokens in CI secrets) to catch upstream changes early.

---

## License

MIT. See [LICENSE](LICENSE).
