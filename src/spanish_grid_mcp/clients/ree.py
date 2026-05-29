"""REE apidatos HTTP client (stub).

Base URL: https://apidatos.ree.es
No auth required for most endpoints.

Real implementation will hit /es/datos/{category}/{widget} with start_date,
end_date, time_trunc params.
"""
from __future__ import annotations

REE_BASE_URL = "https://apidatos.ree.es"
