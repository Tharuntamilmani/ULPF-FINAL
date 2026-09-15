#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# export-images.sh — Pull and export all Docker images for air-gapped deployment
#
# Usage:
#   bash deployment/airgapped/export-images.sh [output_dir]
#
# Output directory defaults to: deployment/airgapped/images/
# Requires: docker, internet access (run on a machine that has internet)
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${1:-${SCRIPT_DIR}/images}"
MANIFEST="${OUTPUT_DIR}/manifest.txt"

mkdir -p "${OUTPUT_DIR}"

# Image list — pinned tags for reproducibility
declare -A IMAGES=(
  ["m6-api"]="ulpf/m6-control-plane:latest"
  ["postgres"]="postgres:16-alpine"
  ["redis"]="redis:7-alpine"
  ["kafka"]="bitnami/kafka:3.7"
  ["minio"]="minio/minio:latest"
  ["opensearch"]="opensearchproject/opensearch:2.14.0"
  ["prometheus"]="prom/prometheus:v2.52.0"
  ["grafana"]="grafana/grafana:10.4.4"
)

echo ""
echo "═══════════════════════════════════════════"
echo "  ULPF M6 Air-Gap Image Export"
echo "═══════════════════════════════════════════"
echo "  Output: ${OUTPUT_DIR}"
echo ""

# Build M6 image first
echo "► Building M6 Control Plane image..."
(cd "${SCRIPT_DIR}/../.." && docker build -t ulpf/m6-control-plane:latest .)

# Pull all images
echo ""
echo "► Pulling images..."
for name in "${!IMAGES[@]}"; do
  img="${IMAGES[$name]}"
  echo "  Pulling: ${img}"
  docker pull "${img}"
done

# Export each image as a .tar file
echo ""
echo "► Exporting images..."
> "${MANIFEST}"

for name in "${!IMAGES[@]}"; do
  img="${IMAGES[$name]}"
  out_file="${OUTPUT_DIR}/${name}.tar"
  echo "  Saving: ${img} → ${name}.tar"
  docker save "${img}" -o "${out_file}"
  size=$(du -sh "${out_file}" | cut -f1)
  echo "${name}|${img}|${name}.tar|${size}" >> "${MANIFEST}"
done

echo ""
echo "► Manifest written to: ${MANIFEST}"
echo ""
cat "${MANIFEST}"

# Compute total size
total=$(du -sh "${OUTPUT_DIR}"/*.tar 2>/dev/null | tail -1 | awk '{print $1}')
echo ""
echo "  Total export size: ~$(du -sh "${OUTPUT_DIR}" | cut -f1)"
echo ""
echo "✓ Export complete. Transfer the '$(basename "${OUTPUT_DIR}")' directory to the air-gapped host."
echo "  Then run: bash deployment/airgapped/import-images.sh"
echo ""
