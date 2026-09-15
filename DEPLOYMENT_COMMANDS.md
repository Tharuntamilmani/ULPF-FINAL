# ULPF — PRODUCTION DEPLOYMENT COMMANDS CHEATSHEET

This document contains copy-pasteable, verified commands for deploying, initializing, running, validating, and managing the ULPF system on a clean host.

---

# SECTION 1 — PREREQUISITES VERIFICATION

Run these commands to verify runtime tools before beginning deployment:

### Windows (PowerShell)
```powershell
python --version
docker --version
docker compose version
node --version
npm --version
git --version
```

### Linux (Bash)
```bash
python3 --version
docker --version
docker compose version
node --version
npm --version
git --version
```

---

# SECTION 2 — WINDOWS PRODUCTION DEPLOYMENT (POWERSHELL)

### 2.1 Host & Directory Preparation
```powershell
# Create local storage directories for persistent state
New-Item -ItemType Directory -Force -Path "E:\ULPF\M1\modules\m1-ingestion\data"
New-Item -ItemType Directory -Force -Path "E:\ULPF\M5\data\datalake"
New-Item -ItemType Directory -Force -Path "E:\ULPF\M5\data\dlq"
New-Item -ItemType Directory -Force -Path "E:\ULPF\integration\config_sync\generated"
New-Item -ItemType Directory -Force -Path "E:\ULPF\integration\scratch\deployment_logs"
```

### 2.2 Infrastructure Container Startup (Docker)
```powershell
# Stop and remove any stale test containers
docker rm -f ulpf-zookeeper ulpf-kafka ulpf-minio ulpf-postgres ulpf-redis ulpf-opensearch 2>$null

# 1. ZooKeeper
docker run -d --name ulpf-zookeeper -p 2181:2181 `
  -e ZOOKEEPER_CLIENT_PORT=2181 `
  -e ZOOKEEPER_TICK_TIME=2000 `
  confluentinc/cp-zookeeper:7.5.0

# 2. Kafka Broker
docker run -d --name ulpf-kafka -p 9092:9092 `
  -e KAFKA_BROKER_ID=1 `
  -e KAFKA_ZOOKEEPER_CONNECT=host.docker.internal:2181 `
  -e KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT `
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092,PLAINTEXT_HOST://localhost:9092 `
  -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 `
  -e KAFKA_AUTO_CREATE_TOPICS_ENABLE="true" `
  confluentinc/cp-kafka:7.5.0

# 3. MinIO S3 Object Storage
docker run -d --name ulpf-minio -p 9000:9000 -p 9001:9001 `
  -e MINIO_ROOT_USER=minioadmin `
  -e MINIO_ROOT_PASSWORD=minioadminsecret `
  minio/minio:latest server /data --console-address ":9001"

# 4. PostgreSQL 15
docker run -d --name ulpf-postgres -p 5432:5432 `
  -e POSTGRES_DB=ulpf_m6 `
  -e POSTGRES_USER=ulpf_admin `
  -e POSTGRES_PASSWORD=ulpf_secure_password `
  postgres:15-alpine

# 5. Redis 7
docker run -d --name ulpf-redis -p 6379:6379 redis:7-alpine

# 6. OpenSearch 2.18
docker run -d --name ulpf-opensearch -p 9200:9200 -p 9600:9600 `
  -e "discovery.type=single-node" `
  -e "plugins.security.disabled=true" `
  -e "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m" `
  opensearchproject/opensearch:2.18.0
```

### 2.3 Persistent Storage & Database Initialization
```powershell
# Wait 10 seconds for databases and Kafka to be ready
Start-Sleep -Seconds 10

# Initialize PostgreSQL schema using Alembic
cd E:\ULPF\M6\M6-SIH-main\backend
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
$env:POSTGRES_DB="ulpf_m6"
$env:POSTGRES_USER="ulpf_admin"
$env:POSTGRES_PASSWORD="ulpf_secure_password"
$env:SECRET_KEY="production-secret-key-minimum-32-characters!!"
$env:ADMIN_PASSWORD="Admin_Secure_Pass_2026!"
alembic upgrade head

# Seed initial Control Plane administrator and metadata
cd E:\ULPF\M6\M6-SIH-main
python scripts/seed.py

# Create MinIO S3 Buckets using dockerized MinIO client
docker run --rm --network host minio/mc alias set local http://localhost:9000 minioadmin minioadminsecret
docker run --rm --network host minio/mc mb local/ulpf-raw
docker run --rm --network host minio/mc mb local/ulpf-datalake
docker run --rm --network host minio/mc mb local/ulpf-contracts
docker run --rm --network host minio/mc mb local/ulpf-schemas

# Pre-create Kafka Topics
docker exec ulpf-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic ulpf.raw --partitions 3 --replication-factor 1
docker exec ulpf-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic ulpf.dlq --partitions 1 --replication-factor 1
docker exec ulpf-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic ulpf.replay --partitions 1 --replication-factor 1
docker exec ulpf-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic ulpf.ai.events --partitions 3 --replication-factor 1
docker exec ulpf-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic ulpf.m6.config.updates --partitions 1 --replication-factor 1
```

### 2.4 Service Dependency Installation
```powershell
# Install dependencies for all microservices
pip install -r E:\ULPF\M1\modules\m1-ingestion\requirements.txt
pip install -r E:\ULPF\M2\abcd-main\requirements.txt
pip install -r E:\ULPF\M3\requirements.txt
pip install -e E:\ULPF\M4
pip install -r E:\ULPF\M5\requirements.txt
pip install -r E:\ULPF\M6\M6-SIH-main\requirements.txt
```

### 2.5 Microservice Startup (Background Processes)
```powershell
# Set Global Python Path
$env:PYTHONPATH="E:\ULPF"

# 1. Start M6 Control Plane (Port 18086 / 8086)
Start-Process -FilePath "python" -ArgumentList "-c", "`"import os; os.environ['SECRET_KEY']='production-secret-key-minimum-32-characters!!'; os.environ['ADMIN_PASSWORD']='Admin_Secure_Pass_2026!'; os.environ['POSTGRES_PASSWORD']='ulpf_secure_password'; os.environ['POSTGRES_USER']='ulpf_admin'; os.environ['POSTGRES_DB']='ulpf_m6'; os.environ['POSTGRES_HOST']='localhost'; os.environ['REDIS_HOST']='localhost'; import sys; sys.path.insert(0, 'E:/ULPF/M6/M6-SIH-main'); from backend.app.main import create_app; import uvicorn; uvicorn.run(create_app(), host='127.0.0.1', port=18086, log_level='info')`"" -WorkingDirectory "E:\ULPF\M6\M6-SIH-main" -RedirectStandardOutput "E:\ULPF\integration\scratch\deployment_logs\M6.log" -RedirectStandardError "E:\ULPF\integration\scratch\deployment_logs\M6_err.log"

# 2. Start Configuration Sync Worker (Port 18081 / 8081)
Start-Process -FilePath "python" -ArgumentList "-c", "`"import os, sys; sys.path.insert(0, 'E:/ULPF'); os.environ['M1_BASE_URL']='http://127.0.0.1:18001'; os.environ['M2_BASE_URL']='http://127.0.0.1:18082'; os.environ['M3_BASE_URL']='http://127.0.0.1:18083'; os.environ['M4_BASE_URL']='http://127.0.0.1:18004'; os.environ['M5_BASE_URL']='http://127.0.0.1:18085'; from integration.config_sync.config_worker import config_sync_app; import uvicorn; uvicorn.run(config_sync_app, host='127.0.0.1', port=18081, log_level='info')`"" -WorkingDirectory "E:\ULPF" -RedirectStandardOutput "E:\ULPF\integration\scratch\deployment_logs\ConfigSync.log" -RedirectStandardError "E:\ULPF\integration\scratch\deployment_logs\ConfigSync_err.log"

# 3. Start M5 Smart Router (Port 18085 / 8085)
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "18085", "--log-level", "info" -WorkingDirectory "E:\ULPF\M5" -RedirectStandardOutput "E:\ULPF\integration\scratch\deployment_logs\M5.log" -RedirectStandardError "E:\ULPF\integration\scratch\deployment_logs\M5_err.log"

# 4. Start M4 Enrichment Engine (Port 18004 / 8004)
Start-Process -FilePath "python" -ArgumentList "-c", "`"from app.main import create_app; import uvicorn; uvicorn.run(create_app(), host='127.0.0.1', port=18004, log_level='info')`"" -WorkingDirectory "E:\ULPF\M4" -RedirectStandardOutput "E:\ULPF\integration\scratch\deployment_logs\M4.log" -RedirectStandardError "E:\ULPF\integration\scratch\deployment_logs\M4_err.log"

# 5. Start M3 UES Normalizer (Port 18083 / 8083)
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "18083", "--log-level", "info" -WorkingDirectory "E:\ULPF\M3" -RedirectStandardOutput "E:\ULPF\integration\scratch\deployment_logs\M3.log" -RedirectStandardError "E:\ULPF\integration\scratch\deployment_logs\M3_err.log"

# 6. Start M2 Parser Engine (Port 18082 / 8082)
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "18082", "--log-level", "info" -WorkingDirectory "E:\ULPF\M2\abcd-main" -RedirectStandardOutput "E:\ULPF\integration\scratch\deployment_logs\M2.log" -RedirectStandardError "E:\ULPF\integration\scratch\deployment_logs\M2_err.log"

# 7. Start M1 Ingestion Service (Port 18001 / 8001)
Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "18001", "--log-level", "info" -WorkingDirectory "E:\ULPF\M1\modules\m1-ingestion" -RedirectStandardOutput "E:\ULPF\integration\scratch\deployment_logs\M1.log" -RedirectStandardError "E:\ULPF\integration\scratch\deployment_logs\M1_err.log"

# 8. Start M1-M2 Kafka Consumer Bridge
Start-Process -FilePath "python" -ArgumentList "-c", "`"import asyncio, sys; sys.path.insert(0, 'E:/ULPF'); from integration.consumers.m1_raw_consumer import M1RawEventConsumer; consumer = M1RawEventConsumer(bootstrap_servers='localhost:9092', m2_base_url='http://127.0.0.1:18082'); asyncio.run(consumer.start())`"" -WorkingDirectory "E:\ULPF" -RedirectStandardOutput "E:\ULPF\integration\scratch\deployment_logs\Bridge.log" -RedirectStandardError "E:\ULPF\integration\scratch\deployment_logs\Bridge_err.log"

# 9. Start Ingress Security Gateway (Port 18080 / 8080)
Start-Process -FilePath "python" -ArgumentList "-c", "`"import os, sys; sys.path.insert(0, 'E:/ULPF'); os.environ['M1_INTERNAL_URL']='http://127.0.0.1:18001'; os.environ['M1_INTERNAL_TOKEN']='sec-m1-token-sysadmin-9901'; from integration.security.ingress_gateway import gateway_app; import uvicorn; uvicorn.run(gateway_app, host='127.0.0.1', port=18080, log_level='info')`"" -WorkingDirectory "E:\ULPF" -RedirectStandardOutput "E:\ULPF\integration\scratch\deployment_logs\Gateway.log" -RedirectStandardError "E:\ULPF\integration\scratch\deployment_logs\Gateway_err.log"

# 10. Start Unified Health Aggregator (Port 18090 / 8090)
Start-Process -FilePath "python" -ArgumentList "-c", "`"import os, sys; sys.path.insert(0, 'E:/ULPF'); os.environ['M1_URL']='http://127.0.0.1:18001'; os.environ['M2_URL']='http://127.0.0.1:18082'; os.environ['M3_URL']='http://127.0.0.1:18083'; os.environ['M4_URL']='http://127.0.0.1:18004'; os.environ['M5_URL']='http://127.0.0.1:18085'; os.environ['M6_URL']='http://127.0.0.1:18086'; os.environ['GATEWAY_URL']='http://127.0.0.1:18080'; os.environ['CONFIG_SYNC_URL']='http://127.0.0.1:18081'; from integration.observability.health import health_app; import uvicorn; uvicorn.run(health_app, host='127.0.0.1', port=18090, log_level='info')`"" -WorkingDirectory "E:\ULPF" -RedirectStandardOutput "E:\ULPF\integration\scratch\deployment_logs\Health.log" -RedirectStandardError "E:\ULPF\integration\scratch\deployment_logs\Health_err.log"
```

### 2.6 Health & Readiness Verification
```powershell
# Query Health Aggregator
curl.exe http://127.0.0.1:18090/health

# Query Individual Services
curl.exe http://127.0.0.1:18080/health  # Ingress Gateway
curl.exe http://127.0.0.1:18001/health  # M1 Ingestion
curl.exe http://127.0.0.1:18082/health  # M2 Parser
curl.exe http://127.0.0.1:18083/health  # M3 Normalizer
curl.exe http://127.0.0.1:18004/health  # M4 Enrichment
curl.exe http://127.0.0.1:18085/health  # M5 Router
curl.exe http://127.0.0.1:18086/health  # M6 Control Plane
curl.exe http://127.0.0.1:18081/health  # ConfigSync
```

### 2.7 Production Smoke Test (Cisco ASA Syslog)
```powershell
# Ingest Cisco ASA syslog via Ingress Security Gateway
$body = "<166>Sep 14 10:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443"

curl.exe -X POST "http://127.0.0.1:18080/v1/ingest/event" `
  -H "Authorization: Bearer key-tenant-cisco-prod" `
  -H "Content-Type: text/plain" `
  -H "X-Source-ID: network-asa-01" `
  --data-binary $body

# Run automated end-to-end integration test
pytest E:\ULPF\integration\tests\e2e\test_real_deployment_network.py -k "test_network_05" -v
```

### 2.8 Graceful Shutdown Commands
```powershell
# Kill port holders for all 9 application services
$ports = @(18080, 18081, 18001, 18082, 18083, 18004, 18085, 18086, 18090)
$lines = netstat -ano
foreach ($p in $ports) {
    foreach ($line in $lines) {
        if ($line -match ":$p\s+.*LISTENING\s+(\d+)") {
            $pidToKill = $matches[1]
            taskkill /F /PID $pidToKill 2>$null
        }
    }
}

# Stop Docker infrastructure
docker stop ulpf-opensearch ulpf-redis ulpf-postgres ulpf-minio ulpf-kafka ulpf-zookeeper
```

---

# SECTION 3 — LINUX PRODUCTION DEPLOYMENT (BASH)

### 3.1 Host & Directory Preparation
```bash
# Create persistent directories
mkdir -p /opt/ulpf/M1/modules/m1-ingestion/data
mkdir -p /opt/ulpf/M5/data/datalake
mkdir -p /opt/ulpf/M5/data/dlq
mkdir -p /opt/ulpf/integration/config_sync/generated
mkdir -p /opt/ulpf/integration/scratch/deployment_logs
```

### 3.2 Infrastructure Container Startup (Docker)
```bash
# Clean previous containers
docker rm -f ulpf-zookeeper ulpf-kafka ulpf-minio ulpf-postgres ulpf-redis ulpf-opensearch 2>/dev/null || true

# 1. ZooKeeper
docker run -d --name ulpf-zookeeper -p 2181:2181 \
  -e ZOOKEEPER_CLIENT_PORT=2181 \
  -e ZOOKEEPER_TICK_TIME=2000 \
  confluentinc/cp-zookeeper:7.5.0

# 2. Kafka Broker
docker run -d --name ulpf-kafka -p 9092:9092 \
  -e KAFKA_BROKER_ID=1 \
  -e KAFKA_ZOOKEEPER_CONNECT=host.docker.internal:2181 \
  -e KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092,PLAINTEXT_HOST://localhost:9092 \
  -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 \
  -e KAFKA_AUTO_CREATE_TOPICS_ENABLE="true" \
  confluentinc/cp-kafka:7.5.0

# 3. MinIO S3
docker run -d --name ulpf-minio -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadminsecret \
  minio/minio:latest server /data --console-address ":9001"

# 4. PostgreSQL 15
docker run -d --name ulpf-postgres -p 5432:5432 \
  -e POSTGRES_DB=ulpf_m6 \
  -e POSTGRES_USER=ulpf_admin \
  -e POSTGRES_PASSWORD=ulpf_secure_password \
  postgres:15-alpine

# 5. Redis 7
docker run -d --name ulpf-redis -p 6379:6379 redis:7-alpine

# 6. OpenSearch 2.18
docker run -d --name ulpf-opensearch -p 9200:9200 -p 9600:9600 \
  -e "discovery.type=single-node" \
  -e "plugins.security.disabled=true" \
  -e "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m" \
  opensearchproject/opensearch:2.18.0
```

### 3.3 Storage & Database Initialization
```bash
sleep 10

# Initialize PostgreSQL schema using Alembic
cd /opt/ulpf/M6/M6-SIH-main/backend
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export POSTGRES_DB="ulpf_m6"
export POSTGRES_USER="ulpf_admin"
export POSTGRES_PASSWORD="ulpf_secure_password"
export SECRET_KEY="production-secret-key-minimum-32-characters!!"
export ADMIN_PASSWORD="Admin_Secure_Pass_2026!"
alembic upgrade head

# Seed initial Control Plane administrator and metadata
cd /opt/ulpf/M6/M6-SIH-main
python3 scripts/seed.py

# Create MinIO S3 Buckets
docker run --rm --network host minio/mc alias set local http://localhost:9000 minioadmin minioadminsecret
docker run --rm --network host minio/mc mb local/ulpf-raw
docker run --rm --network host minio/mc mb local/ulpf-datalake
docker run --rm --network host minio/mc mb local/ulpf-contracts
docker run --rm --network host minio/mc mb local/ulpf-schemas

# Pre-create Kafka Topics
docker exec ulpf-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic ulpf.raw --partitions 3 --replication-factor 1
docker exec ulpf-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic ulpf.dlq --partitions 1 --replication-factor 1
docker exec ulpf-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic ulpf.replay --partitions 1 --replication-factor 1
docker exec ulpf-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic ulpf.ai.events --partitions 3 --replication-factor 1
docker exec ulpf-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic ulpf.m6.config.updates --partitions 1 --replication-factor 1
```

### 3.4 Service Dependency Installation
```bash
pip install -r /opt/ulpf/M1/modules/m1-ingestion/requirements.txt
pip install -r /opt/ulpf/M2/abcd-main/requirements.txt
pip install -r /opt/ulpf/M3/requirements.txt
pip install -e /opt/ulpf/M4
pip install -r /opt/ulpf/M5/requirements.txt
pip install -r /opt/ulpf/M6/M6-SIH-main/requirements.txt
```

### 3.5 Microservice Startup (Background Daemons)
```bash
export PYTHONPATH="/opt/ulpf"

# 1. M6 Control Plane (:18086)
(cd /opt/ulpf/M6/M6-SIH-main && nohup python3 -c "import os; os.environ['SECRET_KEY']='production-secret-key-minimum-32-characters!!'; os.environ['ADMIN_PASSWORD']='Admin_Secure_Pass_2026!'; os.environ['POSTGRES_PASSWORD']='ulpf_secure_password'; os.environ['POSTGRES_USER']='ulpf_admin'; os.environ['POSTGRES_DB']='ulpf_m6'; os.environ['POSTGRES_HOST']='localhost'; os.environ['REDIS_HOST']='localhost'; import sys; sys.path.insert(0, '/opt/ulpf/M6/M6-SIH-main'); from backend.app.main import create_app; import uvicorn; uvicorn.run(create_app(), host='127.0.0.1', port=18086, log_level='info')" > /opt/ulpf/integration/scratch/deployment_logs/M6.log 2>&1 &)

# 2. ConfigSync Worker (:18081)
(cd /opt/ulpf && nohup python3 -c "import os, sys; sys.path.insert(0, '/opt/ulpf'); os.environ['M1_BASE_URL']='http://127.0.0.1:18001'; os.environ['M2_BASE_URL']='http://127.0.0.1:18082'; os.environ['M3_BASE_URL']='http://127.0.0.1:18083'; os.environ['M4_BASE_URL']='http://127.0.0.1:18004'; os.environ['M5_BASE_URL']='http://127.0.0.1:18085'; from integration.config_sync.config_worker import config_sync_app; import uvicorn; uvicorn.run(config_sync_app, host='127.0.0.1', port=18081, log_level='info')" > /opt/ulpf/integration/scratch/deployment_logs/ConfigSync.log 2>&1 &)

# 3. M5 Smart Router (:18085)
(cd /opt/ulpf/M5 && nohup python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18085 --log-level info > /opt/ulpf/integration/scratch/deployment_logs/M5.log 2>&1 &)

# 4. M4 Enrichment (:18004)
(cd /opt/ulpf/M4 && nohup python3 -c "from app.main import create_app; import uvicorn; uvicorn.run(create_app(), host='127.0.0.1', port=18004, log_level='info')" > /opt/ulpf/integration/scratch/deployment_logs/M4.log 2>&1 &)

# 5. M3 Normalizer (:18083)
(cd /opt/ulpf/M3 && nohup python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18083 --log-level info > /opt/ulpf/integration/scratch/deployment_logs/M3.log 2>&1 &)

# 6. M2 Parser (:18082)
(cd /opt/ulpf/M2/abcd-main && nohup python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18082 --log-level info > /opt/ulpf/integration/scratch/deployment_logs/M2.log 2>&1 &)

# 7. M1 Ingestion (:18001)
(cd /opt/ulpf/M1/modules/m1-ingestion && nohup python3 -m uvicorn app.main:app --host 127.0.0.1 --port 18001 --log-level info > /opt/ulpf/integration/scratch/deployment_logs/M1.log 2>&1 &)

# 8. M1-M2 Consumer Bridge
(cd /opt/ulpf && nohup python3 -c "import asyncio, sys; sys.path.insert(0, '/opt/ulpf'); from integration.consumers.m1_raw_consumer import M1RawEventConsumer; consumer = M1RawEventConsumer(bootstrap_servers='localhost:9092', m2_base_url='http://127.0.0.1:18082'); asyncio.run(consumer.start())" > /opt/ulpf/integration/scratch/deployment_logs/Bridge.log 2>&1 &)

# 9. Ingress Gateway (:18080)
(cd /opt/ulpf && nohup python3 -c "import os, sys; sys.path.insert(0, '/opt/ulpf'); os.environ['M1_INTERNAL_URL']='http://127.0.0.1:18001'; os.environ['M1_INTERNAL_TOKEN']='sec-m1-token-sysadmin-9901'; from integration.security.ingress_gateway import gateway_app; import uvicorn; uvicorn.run(gateway_app, host='127.0.0.1', port=18080, log_level='info')" > /opt/ulpf/integration/scratch/deployment_logs/Gateway.log 2>&1 &)

# 10. Health Aggregator (:18090)
(cd /opt/ulpf && nohup python3 -c "import os, sys; sys.path.insert(0, '/opt/ulpf'); os.environ['M1_URL']='http://127.0.0.1:18001'; os.environ['M2_URL']='http://127.0.0.1:18082'; os.environ['M3_URL']='http://127.0.0.1:18083'; os.environ['M4_URL']='http://127.0.0.1:18004'; os.environ['M5_URL']='http://127.0.0.1:18085'; os.environ['M6_URL']='http://127.0.0.1:18086'; os.environ['GATEWAY_URL']='http://127.0.0.1:18080'; os.environ['CONFIG_SYNC_URL']='http://127.0.0.1:18081'; from integration.observability.health import health_app; import uvicorn; uvicorn.run(health_app, host='127.0.0.1', port=18090, log_level='info')" > /opt/ulpf/integration/scratch/deployment_logs/Health.log 2>&1 &)
```

### 3.6 Health & Readiness Verification
```bash
curl -s http://127.0.0.1:18090/health | jq .
```

### 3.7 Production Smoke Test
```bash
curl -X POST http://127.0.0.1:18080/v1/ingest/event \
  -H "Authorization: Bearer key-tenant-cisco-prod" \
  -H "Content-Type: text/plain" \
  -H "X-Source-ID: network-asa-01" \
  --data-binary "<166>Sep 14 10:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443"
```

### 3.8 Graceful Shutdown Commands
```bash
# Terminate microservices
fuser -k 18080/tcp 18081/tcp 18001/tcp 18082/tcp 18083/tcp 18004/tcp 18085/tcp 18086/tcp 18090/tcp 2>/dev/null || true

# Stop Docker infrastructure
docker stop ulpf-opensearch ulpf-redis ulpf-postgres ulpf-minio ulpf-kafka ulpf-zookeeper
```
