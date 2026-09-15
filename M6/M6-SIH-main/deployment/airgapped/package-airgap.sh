#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# package-airgap.sh — Create a complete air-gapped deployment bundle
#
# Produces: deployment/airgapped/ulpf-m6-airgap-<version>.tar.gz
#
# Bundle contents:
#   images/          Docker image tarballs
#   contracts/       JSON schema contracts
#   deployment/      Docker Compose, Prometheus, Grafana config
#   scripts/         seed.py, verify_imports.py
#   .env.example     Environment template
#   README.airgap.md Air-gap specific README
#
# Usage:
#   bash deployment/airgapped/package-airgap.sh
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VERSION="${AIRGAP_VERSION:-$(date +%Y%m%d-%H%M%S)}"
BUNDLE_NAME="ulpf-m6-airgap-${VERSION}"
BUNDLE_DIR="${SCRIPT_DIR}/${BUNDLE_NAME}"
OUTPUT_TAR="${SCRIPT_DIR}/${BUNDLE_NAME}.tar.gz"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ULPF M6 Air-Gap Package Builder"
echo "  Version: ${VERSION}"
echo "═══════════════════════════════════════════════════"
echo ""

# Step 1: Export Docker images
echo "► Step 1/4: Exporting Docker images..."
bash "${SCRIPT_DIR}/export-images.sh" "${BUNDLE_DIR}/images"

# Step 2: Generate contract schemas
echo ""
echo "► Step 2/4: Generating contract schemas..."
python "${PROJECT_ROOT}/contracts/generate_contracts.py"

# Step 3: Assemble bundle
echo ""
echo "► Step 3/4: Assembling bundle..."
mkdir -p "${BUNDLE_DIR}"

# Copy project artefacts
cp -r "${PROJECT_ROOT}/contracts"    "${BUNDLE_DIR}/contracts"
cp -r "${PROJECT_ROOT}/deployment"   "${BUNDLE_DIR}/deployment"
cp -r "${PROJECT_ROOT}/scripts"      "${BUNDLE_DIR}/scripts"
cp -r "${PROJECT_ROOT}/backend"      "${BUNDLE_DIR}/backend"
cp    "${PROJECT_ROOT}/.env.example" "${BUNDLE_DIR}/.env.example"
cp    "${PROJECT_ROOT}/docker-compose.yml" "${BUNDLE_DIR}/docker-compose.yml"
cp    "${PROJECT_ROOT}/requirements.txt"   "${BUNDLE_DIR}/requirements.txt"

# Create air-gap specific .env template
cat > "${BUNDLE_DIR}/.env.airgap" << 'EOF'
# Air-gapped deployment environment template
# Fill in ALL values before running docker compose up

APP_ENV=production
APP_DEBUG=false
LOG_LEVEL=INFO

# REQUIRED: Generate with: openssl rand -hex 32
SECRET_KEY=CHANGE_ME_GENERATE_WITH_OPENSSL_RAND_HEX_32

ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@your-org.local
ADMIN_PASSWORD=CHANGE_ME_STRONG_PASSWORD

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=m6_control_plane
POSTGRES_USER=m6user
POSTGRES_PASSWORD=CHANGE_ME_POSTGRES_PASSWORD

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=

KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_ENABLED=true

MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=CHANGE_ME_MINIO_SECRET

OPENSEARCH_HOST=opensearch
OPENSEARCH_PORT=9200
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=admin
OPENSEARCH_USE_SSL=false
OPENSEARCH_VERIFY_CERTS=false

GRAFANA_USER=admin
GRAFANA_PASSWORD=CHANGE_ME_GRAFANA_PASSWORD

# M1-M5: fill when their services are deployed in your environment
M1_BASE_URL=
M2_BASE_URL=
M3_BASE_URL=
M4_BASE_URL=
M5_BASE_URL=

USE_MOCK_ADAPTERS=false
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
EOF

# Step 4: Create README for air-gap bundle
cat > "${BUNDLE_DIR}/README.airgap.md" << 'EOF'
# ULPF M6 Control Plane — Air-Gapped Deployment

## Prerequisites
- Docker Engine 24+
- Docker Compose v2

## Deployment Steps

### 1. Load Docker images
```bash
bash deployment/airgapped/import-images.sh images/
```

### 2. Configure environment
```bash
cp .env.airgap .env
# Edit .env and fill in all secrets
```

### 3. Start the stack
```bash
docker compose up -d
```

### 4. Wait for services to be healthy
```bash
docker compose ps
# Wait until all services show "healthy"
```

### 5. Run database migrations
```bash
docker compose exec m6-api python -m alembic -c backend/alembic.ini upgrade head
```

### 6. Seed bootstrap data
```bash
docker compose exec m6-api python scripts/seed.py
```

### 7. Access the platform
- API:        http://<host>:8000
- API Docs:   http://<host>:8000/docs
- Grafana:    http://<host>:3000  (admin / <GRAFANA_PASSWORD>)
- Prometheus: http://<host>:9090
- MinIO:      http://<host>:9001

## Verify
```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

## Troubleshooting
- Check logs: `docker compose logs m6-api`
- Postgres not ready: wait 30s for initialization
- Kafka startup: can take up to 60s
EOF

# Step 4: Create archive
echo ""
echo "► Step 4/4: Creating archive..."
tar -czf "${OUTPUT_TAR}" -C "${SCRIPT_DIR}" "${BUNDLE_NAME}/"
rm -rf "${BUNDLE_DIR}"

echo ""
echo "✓ Air-gap bundle created:"
echo "  ${OUTPUT_TAR}"
echo "  Size: $(du -sh "${OUTPUT_TAR}" | cut -f1)"
echo ""
echo "Transfer this file to the air-gapped host, then:"
echo "  tar -xzf $(basename "${OUTPUT_TAR}")"
echo "  cd ${BUNDLE_NAME}"
echo "  bash deployment/airgapped/import-images.sh images/"
echo "  cp .env.airgap .env && vim .env"
echo "  docker compose up -d"
echo ""
