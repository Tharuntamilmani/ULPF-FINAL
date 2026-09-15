# ── ULPF M4 Enrichment Engine Dockerfile ────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

RUN pip install --no-cache-dir pip setuptools wheel

COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install \
    "pydantic>=2.10.0" \
    "pydantic-settings>=2.7.0" \
    "fastapi>=0.115.0" \
    "uvicorn>=0.34.0" \
    "httpx>=0.28.0" \
    "prometheus-client>=0.21.0" \
    "structlog>=24.4.0" \
    "orjson>=3.10.0" \
    "python-dateutil>=2.9.0"

# ── Stage 2: runtime ─────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="ULPF Team"
LABEL version="1.0.0"
LABEL description="ULPF M4 — Enrichment + Provenance + Integrity Engine"

RUN groupadd -r ulpf && useradd -r -g ulpf -d /app -s /sbin/nologin ulpf

WORKDIR /app

COPY --from=builder /install /usr/local
COPY app/ ./app/

RUN chown -R ulpf:ulpf /app

USER ulpf

EXPOSE 8000

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

CMD ["python", "-m", "uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
