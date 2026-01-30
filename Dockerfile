FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY trackings_mcp/ trackings_mcp/
COPY README.md .

RUN pip install --no-cache-dir .

ENV PORT=8000

CMD ["python", "-c", "from trackings_mcp import run_http; run_http()"]
