# spanish-grid-mcp

## Status

**Alpha.** All 10 tools are wired to real HTTP clients (`clients/esios.py`, `clients/ree.py`, `clients/aemet.py`) with disk caching via `cache.py`.

## Setup

```bash
pip install -e ".[dev]"
cp .env.example .env
# fill in ESIOS_TOKEN and AEMET_TOKEN
```

## Commands

| What | Command |
|------|---------|
| Run server (stdio MCP) | `python -m spanish_grid_mcp.server` |
| Run all tests | `pytest` |
| Run single test | `pytest tests/test_server.py::test_all_tools_registered -v` |
| Lint / format check | `ruff check` |
| Lint + fix | `ruff check --fix` |
| Entrypoint (also a console_scripts entry) | `spanish_grid_mcp.server:main` |

## Architecture

- `server.py` — FastMCP app, tool definitions, `main()`. 10 tools wired as real HTTP calls.
- `clients/esios.py` — ESIOS API (`https://api.esios.ree.es`, auth via `x-api-key` header with `ESIOS_TOKEN`).
- `clients/ree.py` — REE apidatos (`https://apidatos.ree.es`, no auth).
- `clients/aemet.py` — AEMET OpenData (`https://opendata.aemet.es/opendata/api`, auth via `api_key` query param with `AEMET_TOKEN`). Uses a two-step fetch pattern.
- `cache.py` — `diskcache.Cache` at `~/.cache/spanish-grid-mcp` (override via `SPANISH_GRID_CACHE_DIR`).

## Conventions

- `dotenv` is loaded at import side effect in `server.py:15` — no need to call `load_dotenv()` manually.
- Ruff config: line-length 100, target `py310`.
- All tests use `pytest-asyncio` (`@pytest.mark.asyncio`).
- Client modules export `is_configured()` helpers — use them in tools to return early when tokens are missing.
- AEMET data requires two HTTP requests: a POST-like GET that returns a data URL, then a GET to that URL.
- REE apidatos rejects `time_trunc=hour` for historical data — use `"day"`. Hourly granularity available via ESIOS.
- AEMET station list uses `/valores/climatologicos/inventarioestaciones/todasestaciones` (station inventory with province metadata), NOT `/observacion/convencional/todas` (which only has observation fields, no `provincia`).
- AEMET station inventory returns province names in UPPERCASE with accents (e.g. `"MADRID"`, `"A CORUÑA"`).
- AEMET ISO-8859-15 encoding: always `resp.content.decode(charset)` not `resp.json()`.
