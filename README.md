# spanish-grid-mcp

An MCP server that exposes Spanish electricity grid data — prices, demand, generation mix, and weather — as tools that any MCP-compatible LLM client (Claude Desktop, custom agents, etc.) can call.

Data sources:
- **ESIOS** (Red Eléctrica) — day-ahead and PVPC prices, ~2000 grid indicators
- **REE apidatos** — demand, generation by technology, cross-border flows
- **AEMET OpenData** — weather observations from Spanish stations

> **Status:** scaffold. Tools are wired but return stub data. See `src/spanish_grid_mcp/clients/*.py` for the integration points.

## Install

```bash
git clone https://github.com/raulrc/spanish-grid-mcp.git
cd spanish-grid-mcp
pip install -e .
cp .env.example .env
# edit .env and add your ESIOS_TOKEN and AEMET_TOKEN
```

## Run standalone (smoke test)

```bash
python -m spanish_grid_mcp.server
```

The server speaks MCP over stdio. With no client attached it will sit waiting for JSON-RPC messages — that's expected. Ctrl-C to exit.

## Use with Claude Desktop

Add this to your `claude_desktop_config.json` (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "spanish-grid": {
      "command": "python",
      "args": ["-m", "spanish_grid_mcp.server"],
      "env": {
        "ESIOS_TOKEN": "your-token-here",
        "AEMET_TOKEN": "your-token-here"
      }
    }
  }
}
```

Then ask Claude things like *"What was the average Spanish day-ahead price yesterday?"* and it'll call the tools.

## Use from a custom agent

See [spanish-grid-research-agent](https://github.com/raulrc/spanish-grid-research-agent) for a Python agent that consumes this server via the Anthropic SDK.

## Tools

| Tool | Description |
|---|---|
| `get_day_ahead_price` | Day-ahead market prices (mercado diario), €/MWh |
| `get_pvpc_price` | PVPC regulated tariff prices, €/MWh per hour |
| `get_demand` | Real, forecast, or scheduled demand, MW |
| `get_generation_mix` | Generation by technology (wind, solar, nuclear, …), MW |
| `get_cross_border_flows` | Imports/exports per border, MW |
| `get_co2_intensity` | Grid CO₂ intensity, gCO₂/kWh |
| `list_weather_stations` | Discover AEMET weather station IDs |
| `get_weather_observations` | Temperature, wind, irradiance from a station |
| `search_esios_indicators` | Free-text search across ESIOS indicators |
| `get_esios_indicator` | Raw access to any ESIOS indicator by ID |

## Credentials

- **ESIOS_TOKEN** — email `consultasios@ree.es` requesting API access. Usually approved within a day.
- **AEMET_TOKEN** — register at https://opendata.aemet.es/centrodedescargas/altaUsuario.

Both are free.

## Caching

Responses are cached to disk (default `~/.cache/spanish-grid-mcp/`) since ESIOS/REE/AEMET data is immutable once published. The cache key includes URL + query params. Override location with `SPANISH_GRID_CACHE_DIR`.

## License

MIT. See [LICENSE](LICENSE).
