# spanish-grid-mcp

**Alpha** — MCP server exposing Spanish electricity grid data as tools for any
MCP-compatible LLM client (Claude Desktop, opencode, custom agents).

```json
// Ask your LLM: "What was the average Spanish day-ahead price yesterday?"
// It calls get_day_ahead_price, gets real data from Red Eléctrica.
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

## Architecture

```
server.py  ← FastMCP app, 10 tool definitions, main()
  │
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
- **Solar irradiance in kWh/m²** — Normalise AEMET solar radiation data to
  standard energy units.
- **Integration tests** — Scheduled tests that exercise the real APIs (with
  tokens in CI secrets) to catch upstream changes early.

---

## License

MIT. See [LICENSE](LICENSE).
