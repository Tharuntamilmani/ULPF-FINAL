# ==============================================================================
# ULPF — Windows Hybrid Deployment Startup Script
# Target: E:\ULPF
# Hardened Orchestration: Delegates to run_stack.py for strict infrastructure
# readiness, Kafka broker probing, and M1-M2 consumer bridge liveness.
# ==============================================================================

param(
    [switch]$CheckOnly,
    [switch]$InfraOnly,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"

$scriptPath = "E:\ULPF\run_stack.py"
$pyArgs = @()

if ($CheckOnly) {
    $pyArgs += "--check-only"
}
if ($InfraOnly) {
    $pyArgs += "--infra-only"
}
if ($Stop) {
    $pyArgs += "--stop"
}

python $scriptPath @pyArgs
exit $LASTEXITCODE
