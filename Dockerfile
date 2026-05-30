FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

EXPOSE 8000

ENV SPANISH_GRID_CACHE_DIR=/data/cache

CMD ["uvicorn", "spanish_grid_mcp.rest:app", "--host", "0.0.0.0", "--port", "8000"]
