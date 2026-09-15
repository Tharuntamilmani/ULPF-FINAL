# ULPF M6 - Pull all required Docker images one by one
# Run from: d:\SIH 2026\m6-control-plane

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  Pulling Docker images for M6 Control Plane" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

$images = @(
    "postgres:16-alpine",
    "redis:7-alpine",
    "bitnami/kafka:3.7",
    "minio/minio:latest",
    "opensearchproject/opensearch:2.14.0",
    "prom/prometheus:v2.52.0",
    "grafana/grafana:10.4.4"
)

$failed = @()

foreach ($img in $images) {
    Write-Host "Pulling: $img ..." -ForegroundColor Yellow
    $attempts = 0
    $success = $false

    while (-not $success -and $attempts -lt 3) {
        $attempts++
        Write-Host "  Attempt $attempts/3..."
        docker pull $img
        if ($LASTEXITCODE -eq 0) {
            $success = $true
            Write-Host "  OK: $img" -ForegroundColor Green
        } else {
            Write-Host "  Failed attempt $attempts. Waiting 5s..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
        }
    }

    if (-not $success) {
        Write-Host "  FAILED after 3 attempts: $img" -ForegroundColor Red
        $failed += $img
    }
    Write-Host ""
}

Write-Host "=======================================================" -ForegroundColor Cyan
if ($failed.Count -eq 0) {
    Write-Host "  All images pulled successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Now run: .\scripts\start-services.ps1" -ForegroundColor White
} else {
    Write-Host "  Failed images:" -ForegroundColor Red
    foreach ($f in $failed) {
        Write-Host "    - $f" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "  Check your internet connection and try again." -ForegroundColor Yellow
}
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""
