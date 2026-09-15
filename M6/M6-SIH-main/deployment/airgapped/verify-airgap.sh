#!/usr/bin/env bash
# verify-airgap.sh — Verify the air-gapped deployment is healthy
set -euo pipefail

BASE_URL="${M6_URL:-http://localhost:8000}"
PASS=0; FAIL=0

check() {
  local name="$1" url="$2" expected="$3"
  local result
  result=$(curl -sf "${url}" 2>/dev/null || echo "FAILED")
  if echo "${result}" | grep -q "${expected}"; then
    echo "  ✓ ${name}"
    ((PASS++))
  else
    echo "  ✗ ${name}  (got: ${result:0:80})"
    ((FAIL++))
  fi
}

echo ""
echo "═══════════════════════════════════════════"
echo "  ULPF M6 Air-Gap Deployment Verification"
echo "  Target: ${BASE_URL}"
echo "═══════════════════════════════════════════"
echo ""
echo "Checking endpoints..."
check "Liveness"    "${BASE_URL}/health"        "ok"
check "Docs"        "${BASE_URL}/docs"           "swagger"
check "Metrics"     "${BASE_URL}/metrics"        ""

echo ""
echo "Checking Docker services..."
for svc in m6-api m6-postgres m6-redis m6-kafka; do
  status=$(docker inspect --format='{{.State.Health.Status}}' "${svc}" 2>/dev/null || echo "not found")
  if [[ "${status}" == "healthy" ]]; then
    echo "  ✓ ${svc}: healthy"
    ((PASS++))
  else
    echo "  ✗ ${svc}: ${status}"
    ((FAIL++))
  fi
done

echo ""
echo "────────────────────────────────────────────"
echo "  Passed: ${PASS}   Failed: ${FAIL}"
if [[ ${FAIL} -eq 0 ]]; then
  echo "  ✓ Air-gapped deployment verified successfully."
else
  echo "  ✗ Some checks failed. Review logs: docker compose logs"
fi
echo ""
