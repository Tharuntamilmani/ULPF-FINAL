# ==============================================================================
# ULPF — Stop Script for Local Deployment
# Target: E:\ULPF
# ==============================================================================

Write-Host "Stopping ULPF Microservices and Consumer Bridge..." -ForegroundColor Yellow

python "E:\ULPF\run_stack.py" --stop

Write-Host "All ULPF native microservices and bridges stopped." -ForegroundColor Green
Write-Host "Note: Docker infrastructure containers (Kafka, MinIO, Redis, OpenSearch, ZooKeeper) were left running." -ForegroundColor Cyan
Write-Host "To stop Docker infrastructure as well, run: docker stop ulpf-opensearch ulpf-redis ulpf-minio ulpf-kafka ulpf-zookeeper" -ForegroundColor Gray
