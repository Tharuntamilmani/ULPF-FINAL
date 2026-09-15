FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root application user
RUN useradd -m -u 1000 appuser

# Copy application files
COPY app/ app/
COPY policies/ policies/

# Create data directories with appropriate ownership
RUN mkdir -p data/datalake data/dlq data/opensearch_storage \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8085

ENV PORT=8085
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8085/health || exit 1

CMD ["python", "-m", "app.main"]
