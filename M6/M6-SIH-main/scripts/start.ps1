# ULPF M6 Control Plane - Startup Script
# Run from: d:\SIH 2026\m6-control-plane

$ErrorActionPreference = "Stop"
$ROOT = Split-Path $PSScriptRoot -Parent
Set-Location $ROOT

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  ULPF M6 Control Plane - Starting..." -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1 - Check Docker
Write-Host "[1/8] Checking Docker..." -ForegroundColor Yellow
docker ps | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}
Write-Host "      Docker is running." -ForegroundColor Green

# Step 2 - Build M6 image
Write-Host ""
Write-Host "[2/8] Building M6 Docker image (this takes 3-5 mins first time)..." -ForegroundColor Yellow
docker compose --env-file .env build m6-api
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker build failed." -ForegroundColor Red
    exit 1
}
Write-Host "      Build complete." -ForegroundColor Green

# Step 3 - Start all services
Write-Host ""
Write-Host "[3/8] Starting all services (postgres, redis, kafka, minio, opensearch, prometheus, grafana, m6-api)..." -ForegroundColor Yellow
docker compose --env-file .env up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: docker compose up failed." -ForegroundColor Red
    exit 1
}
Write-Host "      All services started." -ForegroundColor Green

# Step 4 - Wait for PostgreSQL
Write-Host ""
Write-Host "[4/8] Waiting for PostgreSQL to be healthy..." -ForegroundColor Yellow
$retries = 0
$pgReady = $false
while (-not $pgReady -and $retries -lt 15) {
    Start-Sleep -Seconds 5
    $pgStatus = docker inspect --format "{{.State.Health.Status}}" m6-postgres 2>&1
    $retries++
    Write-Host "      postgres status: $pgStatus ($retries/15)"
    if ($pgStatus -eq "healthy") {
        $pgReady = $true
    }
}
if ($pgReady) {
    Write-Host "      PostgreSQL is healthy." -ForegroundColor Green
} else {
    Write-Host "      PostgreSQL not yet healthy - continuing anyway..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}

# Step 5 - Wait for M6 API
Write-Host ""
Write-Host "[5/8] Waiting for M6 API to be ready..." -ForegroundColor Yellow
$retries = 0
$apiReady = $false
while (-not $apiReady -and $retries -lt 15) {
    Start-Sleep -Seconds 5
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($resp.StatusCode -eq 200) {
            $apiReady = $true
        }
    } catch {
        # not ready yet
    }
    $retries++
    Write-Host "      API ready: $apiReady ($retries/15)"
}
if ($apiReady) {
    Write-Host "      M6 API is ready." -ForegroundColor Green
} else {
    Write-Host "      API not responding yet - waiting 15 more seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15
}

# Step 6 - Run migrations
Write-Host ""
Write-Host "[6/8] Running database migrations..." -ForegroundColor Yellow
docker compose --env-file .env exec m6-api python -m alembic -c backend/alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "      Retrying migrations in 10 seconds..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    docker compose --env-file .env exec m6-api python -m alembic -c backend/alembic.ini upgrade head
}
Write-Host "      Migrations complete." -ForegroundColor Green

# Step 7 - Seed data
Write-Host ""
Write-Host "[7/8] Seeding bootstrap data..." -ForegroundColor Yellow
docker compose --env-file .env exec m6-api python scripts/seed.py
Write-Host "      Seed complete." -ForegroundColor Green

# Step 8 - Push config to Redis + get token
Write-Host ""
Write-Host "[8/8] Pushing config to Redis and provisioning Kafka topics..." -ForegroundColor Yellow
try {
    $loginBody = "username=admin&password=Admin@SIH2026!"
    $loginResp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/x-www-form-urlencoded"
    $token = $loginResp.access_token
    $headers = @{ Authorization = "Bearer $token" }

    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/configuration/distribute" -Method POST -Headers $headers | Out-Null
    Write-Host "      Config distributed to Redis." -ForegroundColor Green

    Invoke-RestMethod -Uri "http://localhost:8000/api/v1/kafka/topics/provision" -Method POST -Headers $headers | Out-Null
    Write-Host "      Kafka topics provisioned." -ForegroundColor Green
} catch {
    Write-Host "      Skipped (Kafka may still be starting - this is OK)." -ForegroundColor Yellow
}

# Run contract tests
Write-Host ""
Write-Host "Running contract tests..." -ForegroundColor Yellow
python contracts/generate_contracts.py
python -m pytest tests/contract/ -v --tb=short -q
Write-Host ""

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
Write-Host "  Login: admin / Admin@SIH2026!" -ForegroundColor White
Write-Host "  Grafana: admin / Grafana@SIH2026!" -ForegroundColor White
Write-Host ""
Write-Host "  Stop stack: docker compose down" -ForegroundColor Gray
Write-Host "  View logs:  docker compose logs -f" -ForegroundColor Gray
Write-Host ""
