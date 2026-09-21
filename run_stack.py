"""
ULPF — Hardened Deployment Orchestrator & Process Supervisor.
Coordinates infrastructure verification, sequential microservice startup,
Kafka readiness probing, M1 /ready Kafka producer verification, and
explicit M1->M2 consumer bridge liveness monitoring.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import time
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

import httpx
import psutil

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

PYTHON_MAIN = sys.executable
PYTHON_M1 = "E:/ULPF/M1/modules/m1-ingestion/.venv/Scripts/python.exe"
PYTHON_M6 = "E:/ULPF/M6/M6-SIH-main/.venv/Scripts/python.exe"

LOG_DIR = "E:/ULPF/integration/scratch/deployment_logs"
PID_FILE = "E:/ULPF/integration/scratch/ulpf_pids.json"
M3_MAPPINGS_DIR = "E:/ULPF/M3/mappings"
os.makedirs(LOG_DIR, exist_ok=True)


class DeploymentState(str, Enum):
    INFRASTRUCTURE_STARTING = "INFRASTRUCTURE_STARTING"
    INFRASTRUCTURE_READY = "INFRASTRUCTURE_READY"
    SERVICES_STARTING = "SERVICES_STARTING"
    SERVICES_READY = "SERVICES_READY"
    PIPELINE_READY = "PIPELINE_READY"
    FAILED = "FAILED"


SERVICES_SPEC: List[Dict[str, Any]] = [
    {
        "name": "M6_Control_Plane",
        "label": "M6",
        "port": 18086,
        "health_url": "http://127.0.0.1:18086/health",
        "python": PYTHON_M6,
        "cmd": [
            PYTHON_M6, "-c",
            "import os; os.environ['SECRET_KEY']='production-secret-key-minimum-32-characters!!'; "
            "os.environ['ADMIN_PASSWORD']='Admin_Secure_Pass_2026!'; "
            "os.environ['POSTGRES_PASSWORD']='ulpf_secure_password'; "
            "os.environ['POSTGRES_USER']='ulpf_admin'; "
            "os.environ['POSTGRES_DB']='ulpf_m6'; "
            "os.environ['POSTGRES_HOST']='localhost'; "
            "os.environ['REDIS_HOST']='localhost'; "
            "import sys; sys.path.insert(0, 'E:/ULPF/M6/M6-SIH-main'); "
            "from backend.app.main import create_app; import uvicorn; "
            "uvicorn.run(create_app(), host='127.0.0.1', port=18086, log_level='info')"
        ],
        "cwd": "E:/ULPF/M6/M6-SIH-main",
        "env": {
            "SECRET_KEY": "production-secret-key-minimum-32-characters!!",
            "ADMIN_PASSWORD": "Admin_Secure_Pass_2026!",
            "POSTGRES_PASSWORD": "ulpf_secure_password",
            "POSTGRES_USER": "ulpf_admin",
            "POSTGRES_DB": "ulpf_m6",
            "POSTGRES_HOST": "localhost",
            "REDIS_HOST": "localhost",
            "M1_BASE_URL": "http://127.0.0.1:18001",
            "M2_BASE_URL": "http://127.0.0.1:18082",
            "M3_BASE_URL": "http://127.0.0.1:18083",
            "M4_BASE_URL": "http://127.0.0.1:18004",
            "M5_BASE_URL": "http://127.0.0.1:18085",
        }
    },
    {
        "name": "ConfigSync_Worker",
        "label": "ConfigSync",
        "port": 18081,
        "health_url": "http://127.0.0.1:18081/health",
        "python": PYTHON_MAIN,
        "cmd": [
            PYTHON_MAIN, "-c",
            "import os, sys; sys.path.insert(0, 'E:/ULPF'); "
            "os.environ['M1_BASE_URL']='http://127.0.0.1:18001'; "
            "os.environ['M2_BASE_URL']='http://127.0.0.1:18082'; "
            "os.environ['M3_BASE_URL']='http://127.0.0.1:18083'; "
            "os.environ['M4_BASE_URL']='http://127.0.0.1:18004'; "
            "os.environ['M5_BASE_URL']='http://127.0.0.1:18085'; "
            "from integration.config_sync.config_worker import config_sync_app; import uvicorn; "
            "uvicorn.run(config_sync_app, host='127.0.0.1', port=18081, log_level='info')"
        ],
        "cwd": "E:/ULPF",
        "env": {
            "M1_BASE_URL": "http://127.0.0.1:18001",
            "M2_BASE_URL": "http://127.0.0.1:18082",
            "M3_BASE_URL": "http://127.0.0.1:18083",
            "M4_BASE_URL": "http://127.0.0.1:18004",
            "M5_BASE_URL": "http://127.0.0.1:18085",
        }
    },
    {
        "name": "M1_Ingestion_Vault",
        "label": "M1",
        "port": 18001,
        "health_url": "http://127.0.0.1:18001/health",
        "ready_url": "http://127.0.0.1:18001/ready",
        "python": PYTHON_M1,
        "cmd": [
            PYTHON_M1, "-c",
            "import sys; sys.path.insert(0, 'E:/ULPF/M1/modules/m1-ingestion'); "
            "from app.main import app; import uvicorn; "
            "uvicorn.run(app, host='127.0.0.1', port=18001, log_level='info')"
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
            "API_AUTH_TOKEN": "sec-m1-token-sysadmin-9901",
        }
    },
    {
        "name": "M2_Parser_Engine",
        "label": "M2",
        "port": 18082,
        "health_url": "http://127.0.0.1:18082/health",
        "python": PYTHON_MAIN,
        "cmd": [
            PYTHON_MAIN, "-c",
            "import sys; sys.path.insert(0, 'E:/ULPF/M2/abcd-main'); "
            "from app.main import app; import uvicorn; "
            "uvicorn.run(app, host='127.0.0.1', port=18082, log_level='info')"
        ],
        "cwd": "E:/ULPF/M2/abcd-main",
        "env": {
            "PARSER_STORAGE_DIR": "E:/ULPF/M2/abcd-main/parsers",
        }
    },
    {
        "name": "M3_UES_Normalizer",
        "label": "M3",
        "port": 18083,
        "health_url": "http://127.0.0.1:18083/health",
        "python": PYTHON_MAIN,
        "cmd": [
            PYTHON_MAIN, "-c",
            "import sys; sys.path.insert(0, 'E:/ULPF/M3'); "
            "from app.main import app; import uvicorn; "
            "uvicorn.run(app, host='127.0.0.1', port=18083, log_level='info')"
        ],
        "cwd": "E:/ULPF/M3",
        "env": {
            "M3_PORT": "18083",
            "M3_CONFIG_PATH": "E:/ULPF/M3/mappings",
        }
    },
    {
        "name": "M4_Enrichment",
        "label": "M4",
        "port": 18004,
        "health_url": "http://127.0.0.1:18004/health",
        "python": PYTHON_MAIN,
        "cmd": [
            PYTHON_MAIN, "-c",
            "from app.main import create_app; import uvicorn; "
            "uvicorn.run(create_app(), host='127.0.0.1', port=18004, log_level='info')"
        ],
        "cwd": "E:/ULPF/M4",
        "env": {}
    },
    {
        "name": "M5_Smart_Router",
        "label": "M5",
        "port": 18085,
        "health_url": "http://127.0.0.1:18085/health",
        "python": PYTHON_MAIN,
        "cmd": [
            PYTHON_MAIN, "-c",
            "import sys; sys.path.insert(0, 'E:/ULPF/M5'); "
            "from app.main import app; import uvicorn; "
            "uvicorn.run(app, host='127.0.0.1', port=18085, log_level='info')"
        ],
        "cwd": "E:/ULPF/M5",
        "env": {
            "OPENSEARCH_HOST": "localhost",
            "OPENSEARCH_PORT": "9200",
            "DISABLE_OPENSEARCH_AUTH": "true",
        }
    },
    {
        "name": "Ingress_Security_Gateway",
        "label": "Gateway",
        "port": 18080,
        "health_url": "http://127.0.0.1:18080/health",
        "python": PYTHON_MAIN,
        "cmd": [
            PYTHON_MAIN, "-c",
            "import os, sys; sys.path.insert(0, 'E:/ULPF'); "
            "os.environ['M1_INTERNAL_URL']='http://127.0.0.1:18001'; "
            "os.environ['M1_INTERNAL_TOKEN']='sec-m1-token-sysadmin-9901'; "
            "from integration.security.ingress_gateway import gateway_app; import uvicorn; "
            "uvicorn.run(gateway_app, host='127.0.0.1', port=18080, log_level='info')"
        ],
        "cwd": "E:/ULPF",
        "env": {
            "M1_INTERNAL_URL": "http://127.0.0.1:18001",
            "M1_INTERNAL_TOKEN": "sec-m1-token-sysadmin-9901",
        }
    },
    {
        "name": "Health_Aggregator",
        "label": "Health Aggregator",
        "port": 18090,
        "health_url": "http://127.0.0.1:18090/live",
        "python": PYTHON_MAIN,
        "cmd": [
            PYTHON_MAIN, "-c",
            "import os, sys; sys.path.insert(0, 'E:/ULPF'); "
            "os.environ['M1_URL']='http://127.0.0.1:18001'; "
            "os.environ['M2_URL']='http://127.0.0.1:18082'; "
            "os.environ['M3_URL']='http://127.0.0.1:18083'; "
            "os.environ['M4_URL']='http://127.0.0.1:18004'; "
            "os.environ['M5_URL']='http://127.0.0.1:18085'; "
            "os.environ['M6_URL']='http://127.0.0.1:18086'; "
            "os.environ['GATEWAY_URL']='http://127.0.0.1:18080'; "
            "os.environ['CONFIG_SYNC_URL']='http://127.0.0.1:18081'; "
            "from integration.observability.health import health_app; import uvicorn; "
            "uvicorn.run(health_app, host='127.0.0.1', port=18090, log_level='info')"
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
            "CONFIG_SYNC_URL": "http://127.0.0.1:18081",
        }
    },
]

NPM_CMD = "npm.cmd" if sys.platform == "win32" else "npm"

UI_SERVICES_SPEC: List[Dict[str, Any]] = [
    {
        "name": "M6_Control_Plane_UI",
        "label": "M6 Frontend UI",
        "port": 5173,
        "health_url": "http://127.0.0.1:5173",
        "cmd": [NPM_CMD, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
        "cwd": "E:/ULPF/M6/M6-SIH-main/frontend",
        "shell": sys.platform == "win32",
        "env": {}
    },
    {
        "name": "M3_Parser_Console_UI",
        "label": "M3 Frontend UI",
        "port": 5174,
        "health_url": "http://127.0.0.1:5174",
        "cmd": [NPM_CMD, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5174"],
        "cwd": "E:/ULPF/M3/frontend",
        "shell": sys.platform == "win32",
        "env": {}
    }
]

BRIDGE_SPEC: Dict[str, Any] = {
    "name": "M1_M2_Consumer_Bridge",
    "label": "M1→M2 Bridge",
    "python": PYTHON_MAIN,
    "cmd": [
        PYTHON_MAIN, "-u", "E:/ULPF/integration/consumers/bridge_runner.py"
    ],
    "cwd": "E:/ULPF",
    "env": {
        "KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
        "M2_BASE_URL": "http://127.0.0.1:18082",
    }
}


def kill_existing_processes(keep_ui: bool = True):
    """Kill any existing port holders and lingering consumer bridges."""
    ports = [18080, 18081, 18001, 18082, 18083, 18004, 18085, 18086, 18090, 18514, 18515]
    if not keep_ui:
        ports.extend([5173, 5174])
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = " ".join(p.info.get('cmdline') or [])
            should_kill = ("M1RawEventConsumer" in cmd or "bridge_runner" in cmd) or (not keep_ui and "vite" in cmd)
            if should_kill:
                try:
                    for child in p.children(recursive=True):
                        child.kill()
                except Exception:
                    pass
                p.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    res = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
    killed = set()
    for line in res.stdout.splitlines():
        for port in ports:
            if f":{port} " in line and ("LISTENING" in line or line.strip().startswith("UDP")):
                pid = line.strip().split()[-1]
                if pid not in killed and pid != "0":
                    try:
                        p_obj = psutil.Process(int(pid))
                        for child in p_obj.children(recursive=True):
                            child.kill()
                    except Exception:
                        pass
                    subprocess.run(["taskkill", "/F", "/T", "/PID", pid], capture_output=True)
                    killed.add(pid)


class InfrastructureVerifier:
    """Verifies and waits for all required infrastructure components."""

    @staticmethod
    def verify_docker_available() -> bool:
        try:
            res = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    @staticmethod
    def ensure_containers_running():
        if os.environ.get("ULPF_SKIP_CONTAINER_START") == "1":
            return
        containers = ["ulpf-zookeeper", "ulpf-kafka", "ulpf-minio", "ulpf-redis", "ulpf-opensearch"]
        for c in containers:
            try:
                inspect = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", c], capture_output=True, text=True)
                if inspect.stdout.strip() != "true":
                    subprocess.run(["docker", "start", c], capture_output=True, timeout=10)
            except Exception as e:
                print(f"   [WARN] Could not inspect/start container {c}: {e}")

    @staticmethod
    def probe_zookeeper(timeout: float = 15.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.5)
                s.connect(('localhost', 2181))
                s.sendall(b'ruok')
                data = s.recv(1024)
                s.close()
                if data:
                    return True
            except Exception:
                pass
            time.sleep(1.0)
        return False

    @staticmethod
    async def probe_kafka(timeout: float = 45.0, required_topic: str = "ulpf.raw", required_group: str = "ulpf-m1-m2-bridge") -> Tuple[bool, str]:
        from aiokafka.admin import AIOKafkaAdminClient, NewTopic
        from aiokafka import AIOKafkaConsumer

        deadline = time.time() + timeout
        backoff = 1.0
        last_err = ""

        while time.time() < deadline:
            try:
                # Check if docker container exited due to ZK restart race and restart if needed
                if os.environ.get("ULPF_SKIP_CONTAINER_START") != "1":
                    inspect = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", "ulpf-kafka"], capture_output=True, text=True)
                    if inspect.stdout.strip() != "true":
                        subprocess.run(["docker", "start", "ulpf-kafka"], capture_output=True, timeout=10)
                        await asyncio.sleep(2.0)

                admin = AIOKafkaAdminClient(bootstrap_servers='localhost:9092', request_timeout_ms=3000)
                await admin.start()
                try:
                    cluster = admin._client.cluster
                    brokers = cluster.brokers()
                    if not brokers:
                        raise RuntimeError("No Kafka brokers found in cluster metadata")

                    topics = await admin.list_topics()
                    if required_topic not in topics:
                        try:
                            await admin.create_topics([NewTopic(name=required_topic, num_partitions=3, replication_factor=1)])
                        except Exception:
                            pass
                        topics = await admin.list_topics()
                        if required_topic not in topics:
                            raise RuntimeError(f"Required topic '{required_topic}' could not be created or accessed")

                    # Verify consumer group support via Kafka Group Coordinator API
                    group_desc = await admin.describe_consumer_groups([required_group])
                    if group_desc and hasattr(group_desc[0], 'groups'):
                        for g in group_desc[0].groups:
                            if g[0] != 0:  # error_code != 0
                                raise RuntimeError(f"Consumer group '{required_group}' coordinator error code {g[0]}")

                    return True, f"Brokers: {len(brokers)}, Topic: {required_topic}, Group: {required_group}"
                finally:
                    await admin.close()
            except Exception as e:
                last_err = str(e)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 1.5, 4.0)

        return False, last_err

    @staticmethod
    def probe_minio(timeout: float = 20.0, required_bucket: str = "ulpf-raw") -> Tuple[bool, str]:
        from minio import Minio
        deadline = time.time() + timeout
        last_err = ""
        while time.time() < deadline:
            try:
                # 1. Check health endpoint (SERVICE_READY)
                r = httpx.get("http://localhost:9000/minio/health/ready", timeout=2.0)
                if r.status_code != 200:
                    last_err = f"HTTP health returned {r.status_code}"
                    time.sleep(1.0)
                    continue

                # 2. Check S3 API and bucket existence (DEPENDENCY_READY)
                mc = Minio("localhost:9000", access_key="minioadmin", secret_key="minioadminsecret", secure=False)
                if not mc.bucket_exists(required_bucket):
                    mc.make_bucket(required_bucket)

                if mc.bucket_exists(required_bucket):
                    return True, f"Bucket '{required_bucket}' ready"
                else:
                    last_err = f"Bucket '{required_bucket}' does not exist"
            except Exception as e:
                last_err = str(e)
            time.sleep(1.0)
        return False, last_err

    @staticmethod
    def probe_redis(timeout: float = 15.0) -> bool:
        import redis
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                r = redis.Redis(host="localhost", port=6379, socket_timeout=2.0)
                if r.ping():
                    return True
            except Exception:
                pass
            time.sleep(1.0)
        return False

    @staticmethod
    def probe_opensearch(timeout: float = 25.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                r = httpx.get("http://localhost:9200/_cluster/health", timeout=2.0)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("status") in ["green", "yellow"]:
                        return True
            except Exception:
                pass
            time.sleep(1.0)
        return False

    @staticmethod
    def probe_postgres(timeout: float = 15.0) -> bool:
        import psycopg2
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                conn = psycopg2.connect(
                    dbname="ulpf_m6",
                    user="ulpf_admin",
                    password="ulpf_secure_password",
                    host="localhost",
                    port=5432,
                    connect_timeout=2
                )
                cur = conn.cursor()
                cur.execute("SELECT 1")
                res = cur.fetchone()
                conn.close()
                if res and res[0] == 1:
                    return True
            except Exception:
                pass
            time.sleep(1.0)
        return False


class DeploymentSupervisor:
    """Hardened orchestrator and process supervisor for ULPF."""

    def __init__(self):
        self.state = DeploymentState.INFRASTRUCTURE_STARTING
        self.procs: List[Tuple[str, subprocess.Popen, Any]] = []
        self.pid_records: Dict[str, Any] = {}
        self.http_client = httpx.Client(timeout=4.0)

    def cleanup(self, signum=None, frame=None):
        print("\nStopping all ULPF services...")
        for name, p, log_f in self.procs:
            try:
                try:
                    p_obj = psutil.Process(p.pid)
                    for child in p_obj.children(recursive=True):
                        child.kill()
                except Exception:
                    pass
                p.terminate()
                p.wait(timeout=2)
            except Exception:
                try:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
                except Exception:
                    pass
            finally:
                try:
                    log_f.close()
                except Exception:
                    pass
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        self.http_client.close()
        print("All ULPF services terminated cleanly.")
        sys.exit(0 if self.state == DeploymentState.PIPELINE_READY else 1)

    def verify_infrastructure(self) -> bool:
        self.state = DeploymentState.INFRASTRUCTURE_STARTING
        if not InfrastructureVerifier.verify_docker_available():
            print("CRITICAL: Docker is not available or not running!")
            self.state = DeploymentState.FAILED
            return False

        InfrastructureVerifier.ensure_containers_running()

        # ZooKeeper
        if not InfrastructureVerifier.probe_zookeeper(timeout=15.0):
            print("CRITICAL: ZooKeeper failed readiness probe on localhost:2181!")
            self.state = DeploymentState.FAILED
            return False
        print("[INFRA] ZooKeeper READY")

        # Kafka
        k_timeout = float(os.environ.get("ULPF_KAFKA_TIMEOUT", "45.0"))
        kafka_ok, kafka_detail = asyncio.run(InfrastructureVerifier.probe_kafka(timeout=k_timeout))
        if not kafka_ok:
            print(f"CRITICAL: Kafka broker failed readiness probe! Error: {kafka_detail}")
            self.state = DeploymentState.FAILED
            return False
        print("[INFRA] Kafka READY")

        # MinIO
        m_timeout = float(os.environ.get("ULPF_MINIO_TIMEOUT", "20.0"))
        minio_ok, minio_detail = InfrastructureVerifier.probe_minio(timeout=m_timeout)
        if not minio_ok:
            print(f"CRITICAL: MinIO failed readiness probe! Error: {minio_detail}")
            self.state = DeploymentState.FAILED
            return False
        print("[INFRA] MinIO READY")

        # Redis
        if not InfrastructureVerifier.probe_redis(timeout=15.0):
            print("CRITICAL: Redis failed readiness probe on localhost:6379!")
            self.state = DeploymentState.FAILED
            return False
        print("[INFRA] Redis READY")

        # OpenSearch
        if not InfrastructureVerifier.probe_opensearch(timeout=25.0):
            print("CRITICAL: OpenSearch failed readiness probe on localhost:9200!")
            self.state = DeploymentState.FAILED
            return False
        print("[INFRA] OpenSearch READY")

        # PostgreSQL
        if not InfrastructureVerifier.probe_postgres(timeout=15.0):
            print("CRITICAL: PostgreSQL failed readiness probe on localhost:5432 (ulpf_m6)!")
            self.state = DeploymentState.FAILED
            return False
        print("[INFRA] PostgreSQL READY")

        self.state = DeploymentState.INFRASTRUCTURE_READY
        return True

    def check_m3_mappings(self):
        """Detect and report known mapping issues per M3 specification."""
        cisco_map = os.path.join(M3_MAPPINGS_DIR, "audit_mapping_cisco.yaml")
        custom_map = os.path.join(M3_MAPPINGS_DIR, "custom_mapping.yaml")
        if os.path.exists(cisco_map) or os.path.exists(custom_map):
            print("   [WARNING] M3 mapping issue detected: 'mappings/audit_mapping_cisco.yaml' and 'mappings/custom_mapping.yaml'")
            print("             are skipped due to schema validation errors. 5 valid mappings remain in cisco/, fortinet/,")
            print("             generic/, paloalto/, windows/. Classification: WARNING (non-blocking for standard syslog smoke tests).")

    def spawn_service(self, spec: Dict[str, Any]) -> subprocess.Popen:
        env = os.environ.copy()
        env.update(spec.get("env", {}))
        log_path = os.path.join(LOG_DIR, f"{spec['name']}.log")
        log_f = open(log_path, "w", buffering=1)
        p = subprocess.Popen(
            spec["cmd"],
            cwd=spec["cwd"],
            env=env,
            shell=spec.get("shell", False),
            stdout=log_f,
            stderr=log_f,
        )
        self.procs.append((spec["name"], p, log_f))
        self.pid_records[spec["name"]] = {
            "pid": p.pid,
            "port": spec.get("port"),
            "health_url": spec.get("health_url"),
            "status": "STARTING",
        }
        return p

    def check_procs_alive(self) -> Optional[Tuple[str, int]]:
        for name, p, _ in self.procs:
            ret = p.poll()
            if ret is not None:
                return name, ret
        return None

    def wait_for_http(self, url: str, timeout: float = 25.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            dead = self.check_procs_alive()
            if dead:
                name, ret = dead
                print(f"CRITICAL: Service {name} died during startup with exit code {ret}!")
                return False
            try:
                r = self.http_client.get(url)
                if r.status_code in (200, 202):
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def wait_for_m1_ready(self, timeout: float = 25.0) -> bool:
        """Verify M1's Kafka producer is operational via M1 /ready endpoint."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            dead = self.check_procs_alive()
            if dead:
                name, ret = dead
                print(f"CRITICAL: Service {name} died during startup with exit code {ret}!")
                return False
            try:
                r = self.http_client.get("http://127.0.0.1:18001/ready")
                if r.status_code == 200:
                    data = r.json()
                    deps = data.get("dependencies", {})
                    if deps.get("kafka") == "up" and deps.get("minio") == "up":
                        return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def verify_bridge_liveness(self, proc: subprocess.Popen, timeout: float = 20.0) -> bool:
        """Verify M1->M2 Bridge process is alive, log confirms startup, and consumer group is active."""
        log_path = os.path.join(LOG_DIR, f"{BRIDGE_SPEC['name']}.log")
        deadline = time.time() + timeout

        # 1. Wait for process startup and log banner
        started_in_log = False
        while time.time() < deadline:
            ret = proc.poll()
            if ret is not None:
                print(f"CRITICAL: M1_M2_Consumer_Bridge failed with exit code {ret}!")
                if os.path.exists(log_path):
                    with open(log_path, "r") as lf:
                        lines = lf.readlines()[-15:]
                        print("   Last log output:\n   " + "   ".join(lines))
                return False

            if os.path.exists(log_path):
                try:
                    with open(log_path, "r") as lf:
                        content = lf.read()
                        if "M1RawEventConsumer started" in content and "ulpf-m1-m2-bridge" in content:
                            started_in_log = True
                            break
                except Exception:
                    pass
            time.sleep(0.5)

        if not started_in_log:
            print("CRITICAL: M1_M2_Consumer_Bridge log did not report consumer loop active within timeout!")
            return False

        # 2. Verify process remains alive for a stabilization window
        for _ in range(4):
            time.sleep(0.5)
            if proc.poll() is not None:
                print(f"CRITICAL: M1_M2_Consumer_Bridge failed during stabilization with exit code {proc.poll()}!")
                return False

        return True

    def start_services(self, with_ui: bool = False) -> bool:
        self.state = DeploymentState.SERVICES_STARTING

        for spec in SERVICES_SPEC:
            name = spec["name"]
            label = spec["label"]

            # M3 mapping pre-check
            if name == "M3_UES_Normalizer":
                self.check_m3_mappings()

            p = self.spawn_service(spec)

            # Wait for service health
            if not self.wait_for_http(spec["health_url"], timeout=30.0):
                print(f"CRITICAL: Service {label} failed HTTP health check at {spec['health_url']}!")
                self.state = DeploymentState.FAILED
                return False

            # Special verification for M1: ensure Kafka producer is active via /ready
            if name == "M1_Ingestion_Vault":
                if not self.wait_for_m1_ready(timeout=20.0):
                    print("CRITICAL: M1 Ingestion reported /health but Kafka producer is down according to /ready!")
                    self.state = DeploymentState.FAILED
                    return False

            self.pid_records[name]["status"] = "READY"
            print(f"[APP] {label} READY")

        self.state = DeploymentState.SERVICES_READY

        # Start M1->M2 Bridge
        p_bridge = self.spawn_service(BRIDGE_SPEC)
        if not self.verify_bridge_liveness(p_bridge, timeout=20.0):
            print("CRITICAL: M1_M2_Consumer_Bridge failed")
            self.state = DeploymentState.FAILED
            return False

        self.pid_records[BRIDGE_SPEC["name"]]["status"] = "READY"
        print("[PIPELINE] M1→M2 Bridge READY")

        # Start Web Frontends if requested
        if with_ui:
            print("\n4. Launching Web Applications (M6 Control Plane & M3 Console)...")
            for spec in UI_SERVICES_SPEC:
                name = spec["name"]
                label = spec["label"]
                p = self.spawn_service(spec)
                if not self.wait_for_http(spec["health_url"], timeout=40.0):
                    print(f"CRITICAL: Web frontend {label} failed HTTP readiness probe at {spec['health_url']}!")
                    self.state = DeploymentState.FAILED
                    return False
                self.pid_records[name]["status"] = "READY"
                print(f"[UI] {label} READY at {spec['health_url']}")

        # Save PID file
        with open(PID_FILE, "w") as f:
            json.dump(self.pid_records, f, indent=2)

        self.state = DeploymentState.PIPELINE_READY
        print("\n============================================")
        print("ULPF INTEGRATED PIPELINE READY")
        if with_ui:
            print("M6 Admin UI : http://127.0.0.1:5173")
            print("M3 Dev UI   : http://127.0.0.1:5174")
        print("============================================")
        print("ALL ULPF INTEGRATED SERVICES ARE HEALTHY AND RUNNING!\n")
        return True

    def run(self, check_only: bool = False, with_ui: bool = False):
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)

        print("=== ULPF Integrated Stack Orchestrator & Supervisor ===")
        print("1. Cleaning stale port holders and previous bridge processes...")
        kill_existing_processes()

        print("\n2. Verifying and probing infrastructure readiness...")
        if not self.verify_infrastructure():
            print("Deployment FAILED at infrastructure phase.")
            sys.exit(1)

        print("\n3. Launching microservices and verifying pipeline...")
        if not self.start_services(with_ui=with_ui):
            print("Deployment FAILED at application/pipeline phase.")
            self.cleanup()
            sys.exit(1)

        if check_only:
            print("[INFO] Check-only mode: all components verified operational. Keeping processes running.")
            return

        # Continuous supervision loop
        try:
            while True:
                time.sleep(2)
                for name, p, _ in self.procs:
                    ret = p.poll()
                    if ret is not None:
                        print(f"CRITICAL: Service {name} (PID {p.pid}) died unexpectedly with exit code {ret}!")
                        if name == "M1_M2_Consumer_Bridge":
                            print("CRITICAL: M1_M2_Consumer_Bridge failed")
                        self.state = DeploymentState.FAILED
                        self.cleanup()
        except KeyboardInterrupt:
            self.cleanup()


def main():
    parser = argparse.ArgumentParser(description="ULPF Deployment Orchestrator")
    parser.add_argument("--check-only", action="store_true", help="Start and verify all services, then exit without blocking")
    parser.add_argument("--infra-only", action="store_true", help="Only verify/start infrastructure datastores")
    parser.add_argument("--stop", action="store_true", help="Stop all running ULPF services cleanly")
    parser.add_argument("--with-ui", action="store_true", help="Start backend services along with M6 and M3 Web Frontends")
    args = parser.parse_args()

    if args.stop:
        print("Stopping all running ULPF microservices and bridge...")
        kill_existing_processes()
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
        print("Stopped cleanly.")
        sys.exit(0)

    supervisor = DeploymentSupervisor()

    if args.infra_only:
        ok = supervisor.verify_infrastructure()
        sys.exit(0 if ok else 1)

    supervisor.run(check_only=args.check_only, with_ui=args.with_ui)


if __name__ == "__main__":
    main()
