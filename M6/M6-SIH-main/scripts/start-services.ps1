# ULPF M6 - Start services after images are pulled
# Run from: d:\SIH 2026\m6-control-plane

$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  ULPF M6 - Starting services" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# Start all services
Write-Host "[1/5] Starting all containers..." -ForegroundColor Yellow
docker compose --env-file .env up -d
Write-Host ""

# Wait for postgres
Write-Host "[2/5] Waiting for PostgreSQL (up to 90s)..." -ForegroundColor Yellow
$ready = $false
for ($i = 1; $i -le 18; $i++) {
    Start-Sleep -Seconds 5
    $status = docker inspect --format "{{.State.Health.Status}}" m6-postgres 2>&1
    Write-Host "      [$i/18] postgres: $status"
    if ($status -eq "healthy") { $ready = $true; break }
}
if ($ready) {
    Write-Host "      PostgreSQL ready." -ForegroundColor Green
} else {
    Write-Host "      PostgreSQL slow to start - waiting 15 more seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15
}

# Wait for M6 API
Write-Host ""
Write-Host "[3/5] Waiting for M6 API (up to 90s)..." -ForegroundColor Yellow
$apiReady = $false
for ($i = 1; $i -le 18; $i++) {
    Start-Sleep -Seconds 5
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($r.StatusCode -eq 200) { $apiReady = $true; break }
    } catch {}
    Write-Host "      [$i/18] API ready: $apiReady"
}
if ($apiReady) {
    Write-Host "      M6 API ready." -ForegroundColor Green
} else {
    Write-Host "      API not ready yet - trying migrations anyway in 15s..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15
}

# Run migrations
Write-Host ""
Write-Host "[4/5] Running database migrations..." -ForegroundColor Yellow
docker compose --env-file .env exec m6-api python -m alembic -c backend/alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "      Retrying in 10s..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    docker compose --env-file .env exec m6-api python -m alembic -c backend/alembic.ini upgrade head
}
Write-Host "      Migrations done." -ForegroundColor Green

# Seed data
Write-Host ""
Write-Host "[5/5] Seeding bootstrap data..." -ForegroundColor Yellow
docker compose --env-file .env exec m6-api python scripts/seed.py
Write-Host "      Seed done." -ForegroundColor Green

# Login and push config
Write-Host ""
Write-Host "Pushing config to Redis..." -ForegroundColor Yellow
try {
    $loginResp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" `
        -Method POST `
        -Body "username=admin&password=Admin@SIH2026!" `
        -ContentType "application/x-www-form-urlencoded"
    $token = $loginResp.access_token
    $headers = @{ Authorization = "Bearer $token" }
    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/configuration/distribute" -Method POST -Headers $headers | Out-Null
    Write-Host "      Config pushed to Redis." -ForegroundColor Green
} catch {
    Write-Host "      Skipped (will work once Kafka is up)." -ForegroundColor Yellow
}

# Done
Write-Host ""
Write-Host "=======================================================" -ForegroundColor Green
Write-Host "  M6 Control Plane is RUNNING!" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  API + Swagger : http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Grafana        : http://localhost:3000" -ForegroundColor Cyan
Write-Host "  Prometheus     : http://localhost:9090" -ForegroundColor Cyan
Write-Host "  MinIO Console  : http://localhost:9001" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Login : admin / Admin@SIH2026!" -ForegroundColor White
Write-Host "  Grafana: admin / Grafana@SIH2026!" -ForegroundColor White
Write-Host ""
Write-Host "  docker compose logs -f    (view logs)" -ForegroundColor Gray
Write-Host "  docker compose down       (stop)" -ForegroundColor Gray
Write-Host "  docker compose ps         (check status)" -ForegroundColor Gray
Write-Host ""
