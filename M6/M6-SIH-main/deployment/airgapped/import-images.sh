#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# import-images.sh — Load Docker images on the air-gapped host
#
# Usage:
#   bash deployment/airgapped/import-images.sh [images_dir]
#
# Defaults to: deployment/airgapped/images/
# Requires: docker (no internet needed)
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGES_DIR="${1:-${SCRIPT_DIR}/images}"
MANIFEST="${IMAGES_DIR}/manifest.txt"

echo ""
echo "═══════════════════════════════════════════"
echo "  ULPF M6 Air-Gap Image Import"
echo "═══════════════════════════════════════════"
echo "  Images dir: ${IMAGES_DIR}"
echo ""

if [[ ! -d "${IMAGES_DIR}" ]]; then
  echo "ERROR: Images directory not found: ${IMAGES_DIR}"
  echo "       Run export-images.sh on a networked machine first."
  exit 1
fi

# Load from manifest if it exists, else load all .tar files
if [[ -f "${MANIFEST}" ]]; then
  echo "► Loading from manifest..."
  while IFS='|' read -r name img tar_file size; do
    full_path="${IMAGES_DIR}/${tar_file}"
    if [[ -f "${full_path}" ]]; then
      echo "  Loading: ${tar_file} (${size}) → ${img}"
      docker load -i "${full_path}"
    else
      echo "  WARNING: ${tar_file} not found, skipping."
    fi
  done < "${MANIFEST}"
else
  echo "► No manifest found — loading all .tar files..."
  for tar in "${IMAGES_DIR}"/*.tar; do
    echo "  Loading: $(basename "${tar}")"
    docker load -i "${tar}"
  done
fi

echo ""
echo "► Verifying loaded images..."
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}" | grep -E "ulpf|postgres|redis|kafka|minio|opensearch|prometheus|grafana" || true

echo ""
echo "✓ Image import complete."
echo ""
echo "Next steps:"
echo "  1. Copy your .env file:  cp deployment/airgapped/.env.airgap .env"
echo "  2. Edit secrets in .env (SECRET_KEY, POSTGRES_PASSWORD, etc.)"
echo "  3. Start the stack:      docker compose up -d"
echo "  4. Run migrations:       docker compose exec m6-api alembic upgrade head"
echo "  5. Seed data:            docker compose exec m6-api python scripts/seed.py"
echo ""
