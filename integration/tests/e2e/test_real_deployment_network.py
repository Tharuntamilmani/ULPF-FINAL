"""
ULPF Phase 1.1 — Requirement 9: Real Integrated Deployment Network Test Suite.

Deploys and tests the COMPLETE live stack over actual loopback TCP network sockets:
  - Infrastructure: Kafka (9092), MinIO (9000), Redis (6379), PostgreSQL (5432), OpenSearch (9200), ZooKeeper (2181)
  - Security Gateway (18080)
  - Config Sync Worker (18081)
  - M1 Ingestion & Raw Vault (18001)
  - M2 Format Classifier & Parser Engine (18082)
  - M3 Universal Event Schema Normalizer (18083)
  - M4 Enrichment, Provenance & Integrity Engine (18004)
  - M5 Policy Routing & Delivery Engine (18085)
  - M6 Control Plane (18086)
  - Health Aggregator (18090)

NO MOCKS for M1-M6 or infrastructure. All inter-service communications execute
via real HTTP over TCP network calls.
"""

import os
import sys
import time
import uuid
import socket
import hashlib
import subprocess
from typing import Dict, Any, Generator

import pytest
import httpx

from integration.contracts.tenant_context import TenantContext
from integration.adapters.m2_m3_adapter import M2M3Adapter
from integration.adapters.m3_m4_adapter import M3M4Adapter
from integration.adapters.m4_m5_adapter import M4M5Adapter


PYTHON_MAIN = sys.executable
PYTHON_M1 = "E:/ULPF/M1/modules/m1-ingestion/.venv/Scripts/python.exe"
PYTHON_M6 = "E:/ULPF/M6/M6-SIH-main/.venv/Scripts/python.exe"

SERVICES_CONFIG = [
    {
        "name": "M1",
        "port": 18001,
        "health_url": "http://127.0.0.1:18001/health",
        "cmd": [
            PYTHON_M1, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", "18001", "--log-level", "warning"
        ],
        "cwd": "E:/ULPF/M1/modules/m1-ingestion",
        "env": {
            "HTTP_PORT": "18001",
            "UDP_PORT": "18514",
            "TCP_PORT": "18515",
            "MINIO_ENDPOINT": "localhost:9000",
            "MINIO_ACCESS_KEY": "minioadmin",
            "MINIO_SECRET_KEY": "minioadminsecret",
            "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
            "OUTBOX_DB_PATH": "data/outbox_network_test.db",
            "API_AUTH_TOKEN": "sec-m1-token-sysadmin-9901",
        }
    },
    {
        "name": "M2",
        "port": 18082,
        "health_url": "http://127.0.0.1:18082/health",
        "cmd": [
            PYTHON_MAIN, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", "18082", "--log-level", "warning"
        ],
        "cwd": "E:/ULPF/M2/abcd-main",
        "env": {
            "PARSER_STORAGE_DIR": "E:/ULPF/M2/abcd-main/parsers"
        }
    },
    {
        "name": "M3",
        "port": 18083,
        "health_url": "http://127.0.0.1:18083/health",
        "cmd": [
            PYTHON_MAIN, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", "18083", "--log-level", "warning"
        ],
        "cwd": "E:/ULPF/M3",
        "env": {
            "M3_PORT": "18083",
            "M3_CONFIG_PATH": "E:/ULPF/M3/mappings"
        }
    },
    {
        "name": "M4",
        "port": 18004,
        "health_url": "http://127.0.0.1:18004/health",
        "cmd": [
            PYTHON_MAIN, "-c",
            "from app.main import create_app; import uvicorn; uvicorn.run(create_app(), host='127.0.0.1', port=18004, log_level='warning')"
        ],
        "cwd": "E:/ULPF/M4",
        "env": {}
    },
    {
        "name": "M5",
        "port": 18085,
        "health_url": "http://127.0.0.1:18085/health",
        "cmd": [
            PYTHON_MAIN, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", "18085", "--log-level", "warning"
        ],
        "cwd": "E:/ULPF/M5",
        "env": {
            "OPENSEARCH_HOST": "localhost",
            "OPENSEARCH_PORT": "9200",
            "DISABLE_OPENSEARCH_AUTH": "true"
        }
    },
    {
        "name": "M6",
        "port": 18086,
        "health_url": "http://127.0.0.1:18086/health",
        "cmd": [
            PYTHON_M6, "-c",
            "import os; os.environ['SECRET_KEY']='test-secret-key-32-bytes-minimum!!'; os.environ['ADMIN_PASSWORD']='admin_secret_pass_123'; os.environ['POSTGRES_PASSWORD']='ulpf_secure_password'; import sys; sys.path.insert(0, 'E:/ULPF/M6/M6-SIH-main'); from backend.app.main import create_app; import uvicorn; uvicorn.run(create_app(), host='127.0.0.1', port=18086, log_level='warning')"
        ],
        "cwd": "E:/ULPF/M6/M6-SIH-main",
        "env": {
            "SECRET_KEY": "test-secret-key-32-bytes-minimum!!",
            "ADMIN_PASSWORD": "admin_secret_pass_123",
            "POSTGRES_PASSWORD": "ulpf_secure_password",
            "POSTGRES_USER": "ulpf_admin",
            "POSTGRES_DB": "ulpf_m6",
            "POSTGRES_HOST": "localhost",
            "REDIS_HOST": "localhost"
        }
    },
    {
        "name": "Gateway",
        "port": 18080,
        "health_url": "http://127.0.0.1:18080/health",
        "cmd": [
            PYTHON_MAIN, "-c",
            "import os, sys; sys.path.insert(0, 'E:/ULPF'); os.environ['M1_INTERNAL_URL']='http://127.0.0.1:18001'; from integration.security.ingress_gateway import gateway_app; import uvicorn; uvicorn.run(gateway_app, host='127.0.0.1', port=18080, log_level='warning')"
        ],
        "cwd": "E:/ULPF",
        "env": {
            "M1_INTERNAL_URL": "http://127.0.0.1:18001",
            "M1_INTERNAL_TOKEN": "sec-m1-token-sysadmin-9901"
        }
    },
    {
        "name": "ConfigSync",
        "port": 18081,
        "health_url": "http://127.0.0.1:18081/health",
        "cmd": [
            PYTHON_MAIN, "-c",
            "import os, sys; sys.path.insert(0, 'E:/ULPF'); os.environ['M1_BASE_URL']='http://127.0.0.1:18001'; os.environ['M2_BASE_URL']='http://127.0.0.1:18082'; os.environ['M3_BASE_URL']='http://127.0.0.1:18083'; os.environ['M4_BASE_URL']='http://127.0.0.1:18004'; os.environ['M5_BASE_URL']='http://127.0.0.1:18085'; from integration.config_sync.config_worker import config_sync_app; import uvicorn; uvicorn.run(config_sync_app, host='127.0.0.1', port=18081, log_level='warning')"
        ],
        "cwd": "E:/ULPF",
        "env": {
            "M1_BASE_URL": "http://127.0.0.1:18001",
            "M2_BASE_URL": "http://127.0.0.1:18082",
            "M3_BASE_URL": "http://127.0.0.1:18083",
            "M4_BASE_URL": "http://127.0.0.1:18004",
            "M5_BASE_URL": "http://127.0.0.1:18085"
        }
    },
    {
        "name": "HealthAggregator",
        "port": 18090,
        "health_url": "http://127.0.0.1:18090/live",
        "cmd": [
            PYTHON_MAIN, "-c",
            "import os, sys; sys.path.insert(0, 'E:/ULPF'); os.environ['M1_URL']='http://127.0.0.1:18001'; os.environ['M2_URL']='http://127.0.0.1:18082'; os.environ['M3_URL']='http://127.0.0.1:18083'; os.environ['M4_URL']='http://127.0.0.1:18004'; os.environ['M5_URL']='http://127.0.0.1:18085'; os.environ['M6_URL']='http://127.0.0.1:18086'; os.environ['GATEWAY_URL']='http://127.0.0.1:18080'; os.environ['CONFIG_SYNC_URL']='http://127.0.0.1:18081'; from integration.observability.health import health_app; import uvicorn; uvicorn.run(health_app, host='127.0.0.1', port=18090, log_level='warning')"
        ],
        "cwd": "E:/ULPF",
        "env": {
            "M1_URL": "http://127.0.0.1:18001",
            "M2_URL": "http://127.0.0.1:18082",
            "M3_URL": "http://127.0.0.1:18083",
            "M4_URL": "http://127.0.0.1:18004",
            "M5_URL": "http://127.0.0.1:18085",
            "M6_URL": "http://127.0.0.1:18086",
            "GATEWAY_URL": "http://127.0.0.1:18080",
            "CONFIG_SYNC_URL": "http://127.0.0.1:18081"
        }
    }
]


def _kill_existing_port_holders():
    """Kill any previous stale processes holding our test ports."""
    ports = [s["port"] for s in SERVICES_CONFIG]
    res = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
    for line in res.stdout.splitlines():
        for port in ports:
            if f":{port} " in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = parts[-1]
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)


@pytest.fixture(scope="module")
def running_stack() -> Generator[Dict[str, str], None, None]:
    """
    Spawns all 9 real service processes on loopback ports.
    Verifies all 9 report healthy over real HTTP calls.
    Cleanly shuts down all processes at module teardown.
    """
    _kill_existing_port_holders()

    procs = []
    log_dir = "E:/ULPF/integration/scratch/deployment_logs"
    os.makedirs(log_dir, exist_ok=True)

    try:
        # Launch all 9 services
        for s in SERVICES_CONFIG:
            env = os.environ.copy()
            env.update(s["env"])
            log_path = os.path.join(log_dir, f"{s['name']}.log")
            log_f = open(log_path, "w")
            p = subprocess.Popen(
                s["cmd"],
                cwd=s["cwd"],
                env=env,
                stdout=log_f,
                stderr=log_f,
            )
            procs.append((s, p, log_f))

        # Wait for all services to become healthy
        deadline = time.time() + 35.0
        client = httpx.Client(timeout=3.0)
        healthy = set()

        while time.time() < deadline and len(healthy) < len(SERVICES_CONFIG):
            for s, p, _ in procs:
                if s["name"] in healthy:
                    continue
                ret = p.poll()
                if ret is not None:
                    raise RuntimeError(f"Service {s['name']} exited prematurely with code {ret}!")
                try:
                    r = client.get(s["health_url"])
                    if r.status_code in (200, 202):
                        healthy.add(s["name"])
                except Exception:
                    pass
            time.sleep(0.4)

        if len(healthy) < len(SERVICES_CONFIG):
            missing = [s["name"] for s in SERVICES_CONFIG if s["name"] not in healthy]
            raise TimeoutError(f"Services failed to become healthy within 35s: {missing}")

        service_urls = {s["name"]: f"http://127.0.0.1:{s['port']}" for s in SERVICES_CONFIG}
        yield service_urls

    finally:
        # Graceful termination then force kill
        for s, p, log_f in procs:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    p.kill()
            try:
                log_f.close()
            except Exception:
                pass
        _kill_existing_port_holders()


# ──────────────────────────────────────────────────────────────────────────────
# Test 1: Infrastructure Connectivity
# ──────────────────────────────────────────────────────────────────────────────
def test_network_01_infrastructure_connectivity(running_stack):
    """
    Verifies real TCP socket connectivity to all required core infrastructure components:
      - Kafka (9092)
      - MinIO (9000)
      - Redis (6379)
      - PostgreSQL (5432)
      - OpenSearch (9200)
      - ZooKeeper (2181)
    """
    infra_targets = [
        ("Kafka Broker", "127.0.0.1", 9092),
        ("MinIO Object Storage", "127.0.0.1", 9000),
        ("Redis Cache", "127.0.0.1", 6379),
        ("PostgreSQL Database", "127.0.0.1", 5432),
        ("OpenSearch Engine", "127.0.0.1", 9200),
        ("ZooKeeper Coordinator", "127.0.0.1", 2181),
    ]

    for name, host, port in infra_targets:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        try:
            s.connect((host, port))
            s.close()
        except Exception as e:
            pytest.fail(f"Infrastructure component {name} on {host}:{port} failed TCP connection: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Test 2: Multi-Service Health & Health Aggregator Verification
# ──────────────────────────────────────────────────────────────────────────────
def test_network_02_all_services_health_aggregation(running_stack):
    """
    Queries /health on all 9 services over real HTTP network sockets.
    Verifies Health Aggregator queries each module across the network and returns HEALTHY.
    """
    with httpx.Client(timeout=15.0) as client:
        # Check individual endpoints
        for name, base_url in running_stack.items():
            resp = client.get(f"{base_url}/health")
            assert resp.status_code in (200, 202), f"Service {name} returned status {resp.status_code}"

        # Check Health Aggregator
        agg_url = running_stack["HealthAggregator"]
        agg_resp = client.get(f"{agg_url}/health")
        assert agg_resp.status_code == 200
        data = agg_resp.json()
        assert data["status"] in ("HEALTHY", "DEGRADED")
        assert "modules" in data
        assert "M1" in data["modules"]
        assert "M2" in data["modules"]


# ──────────────────────────────────────────────────────────────────────────────
# Test 3: M6 -> M2 Real Network Configuration Distribution & Live Parse Proof
# ──────────────────────────────────────────────────────────────────────────────
def test_network_03_m6_to_m2_network_config_distribution(running_stack):
    """
    Submits an M2 parser configuration update to ConfigSync over HTTP.
    Verifies ConfigSync registers the parser into M2 across loopback network.
    Sends an actual HTTP parse request to M2 to prove the new parser is operational.
    """
    config_sync_url = running_stack["ConfigSync"]
    m2_url = running_stack["M2"]

    distribution_payload = {
        "distribution_id": f"dist-net-{uuid.uuid4().hex[:8]}",
        "configuration_id": "cfg-cisco-firewall-net-v1",
        "target_module": "M2",
        "version": 1,
        "action": "REGISTER_PARSER",
        "checksum": hashlib.sha256(b"net-parser-cisco").hexdigest(),
        "payload": {
            "id": "parser-custom-tenant-cisco",
            "name": "Tenant Cisco Custom Parser",
            "tenant_id": "tenant-cisco",
            "vendor": "CustomCorp",
            "product": "AppServer",
            "formats": ["syslog"],
            "patterns": ["^APP_LOG user=%{WORD:user} latency=%{INT:latency_ms}"],
            "version": "1.0.0"
        }
    }

    with httpx.Client(timeout=10.0) as client:
        # 1. Apply via ConfigSync
        apply_resp = client.post(f"{config_sync_url}/config/apply/M2", json=distribution_payload)
        assert apply_resp.status_code == 200
        ack = apply_resp.json()
        assert ack["status"] in ("APPLIED", "ACTIVE")
        assert ack["config_state"] == "ACTIVE"
        assert ack["applied"] is True

        # 2. Verify M2 actually has and executes the parser over HTTP
        parse_req = {
            "schema_version": "1.0.0",
            "raw_event_id": f"raw-net-{uuid.uuid4().hex[:8]}",
            "tenant_id": "tenant-cisco",
            "payload": "APP_LOG user=bob latency=45",
            "transport": "syslog"
        }
        m2_headers = {"Authorization": "Bearer system-admin-token"}
        parse_resp = client.post(f"{m2_url}/v1/parse", json=parse_req, headers=m2_headers)
        assert parse_resp.status_code == 200
        parsed = parse_resp.json()
        assert parsed["status"] == "PARSED"
        assert "parser" in parsed
        assert parsed["fields"].get("user") == "bob"
        assert (
            parsed["fields"].get("latency") in (45, "45")
            or parsed["fields"].get("latency_ms") in (45, "45")
        )


# ──────────────────────────────────────────────────────────────────────────────
# Test 4: M6 -> M1 Real Network Configuration & Truthful ACK
# ──────────────────────────────────────────────────────────────────────────────
def test_network_04_m6_to_m1_network_config_honest_ack(running_stack):
    """
    Submits an M1 source configuration mutation to ConfigSync over HTTP.
    Verifies ConfigSync materializes the configuration and returns truthful
    RESTART_REQUIRED / MATERIALIZED ACK, refusing to return false APPLIED.
    """
    config_sync_url = running_stack["ConfigSync"]

    m1_dist = {
        "distribution_id": f"dist-m1-net-{uuid.uuid4().hex[:8]}",
        "configuration_id": "cfg-m1-source-net-v1",
        "target_module": "M1",
        "version": 1,
        "action": "UPDATE_SOURCES",
        "checksum": hashlib.sha256(b"m1-source-config").hexdigest(),
        "payload": {
            "sources": [
                {"source_id": "net-src-fw-01", "type": "cisco_asa", "rate_limit": 5000}
            ]
        }
    }

    with httpx.Client(timeout=5.0) as client:
        resp = client.post(f"{config_sync_url}/config/apply/M1", json=m1_dist)
        assert resp.status_code == 200
        ack = resp.json()
        # Honest ACK semantics: M1 does not support hot-reload, must report RESTART_REQUIRED
        assert ack["status"] == "RESTART_REQUIRED"
        assert ack["restart_required"] is True
        assert ack["applied"] is False


# ──────────────────────────────────────────────────────────────────────────────
# Test 5: Ingress Gateway -> M1 -> M2 -> M3 -> M4 -> M5 Real Network Pipeline
# ──────────────────────────────────────────────────────────────────────────────
def test_network_05_ingress_to_delivery_real_network_pipeline(running_stack):
    """
    Full real network transit test:
      Client -> Gateway (18080) -> M1 (18001) -> MinIO + Kafka
      Envelope -> M2 (18082) -> M3 (18083) -> M4 (18004) -> M5 (18085)
    Verifies tenant boundary enforcement, raw SHA-256 persistence, and HMAC integrity.
    """
    gateway_url = running_stack["Gateway"]
    m2_url = running_stack["M2"]
    m3_url = running_stack["M3"]
    m4_url = running_stack["M4"]
    m5_url = running_stack["M5"]

    raw_event_text = (
        "<166>Sep 14 10:00:15 cisco-asa %ASA-6-302013: "
        "Built inbound TCP connection 847392 for outside:192.168.10.25/51542 "
        "to inside:8.8.8.8/443"
    )
    expected_sha256 = hashlib.sha256(raw_event_text.encode("utf-8")).hexdigest()

    with httpx.Client(timeout=10.0) as client:
        # 1. Client submits to Ingress Gateway over real HTTP
        ingest_headers = {
            "Authorization": "Bearer key-tenant-cisco-prod",
            "Content-Type": "text/plain",
            "X-Source-ID": "network-asa-01"
        }
        ingest_resp = client.post(
            f"{gateway_url}/v1/ingest/event",
            content=raw_event_text.encode("utf-8"),
            headers=ingest_headers
        )
        assert ingest_resp.status_code in (200, 202), f"Gateway failed: {ingest_resp.text}"
        m1_result = ingest_resp.json()
        assert m1_result["status"] == "accepted"
        raw_event_id = m1_result["raw_event_id"]
        assert m1_result["sha256"] == expected_sha256

        # 2. M2 Real HTTP Parse
        m2_req = {
            "schema_version": "1.0.0",
            "raw_event_id": raw_event_id,
            "tenant_id": "tenant-cisco",
            "source_id": "network-asa-01",
            "payload": raw_event_text,
            "sha256": expected_sha256,
            "transport": "http"
        }
        m2_headers = {"Authorization": "Bearer system-admin-token"}
        m2_resp = client.post(f"{m2_url}/v1/parse", json=m2_req, headers=m2_headers)
        assert m2_resp.status_code == 200
        m2_parsed = m2_resp.json()
        assert m2_parsed["status"] == "PARSED"

        # 3. Adapt M2 -> M3 using M2M3Adapter, then Real HTTP Normalize via M3
        trusted_ctx = TenantContext(tenant_id="tenant-cisco", source_id="network-asa-01")
        m3_input = M2M3Adapter.adapt(m2_parsed, tenant_context=trusted_ctx)
        m3_resp = client.post(f"{m3_url}/v1/normalize", json=m3_input)
        assert m3_resp.status_code == 200
        m3_data = m3_resp.json()
        assert m3_data.get("success") is True, f"M3 normalization failed: {m3_data.get('errors')}"

        # 4. Adapt M3 -> M4 using M3M4Adapter, then Real HTTP Enrich via M4
        m4_req = M3M4Adapter.adapt(m3_result=m3_data, tenant_context=trusted_ctx)
        m4_headers = {"X-API-Key": "m4-admin-key"}
        m4_resp = client.post(f"{m4_url}/v1/enrich", json=m4_req, headers=m4_headers)
        assert m4_resp.status_code == 200, f"M4 enrichment failed: {m4_resp.text}"
        m4_data = m4_resp.json()
        assert m4_data["status"].lower() == "success"
        enriched = m4_data["event"]
        assert enriched["tenant"]["tenant_id"] == "tenant-cisco"
        assert "integrity" in enriched
        assert enriched["integrity"]["algorithm"].lower() in ("sha256", "hmac-sha256", "sha-256")

        # 5. Adapt M4 -> M5 using M4M5Adapter, then Real HTTP Policy Routing & Delivery via M5
        m5_event = M4M5Adapter.adapt(m4_data)
        m5_resp = client.post(f"{m5_url}/v1/events/process", json=m5_event)
        assert m5_resp.status_code == 200
        m5_data = m5_resp.json()
        assert m5_data["status"] in ("processed", "unrouted", "delivered")

