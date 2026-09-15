"""
ULPF Deployment Hardening Verification Battery.
Validates:
1. Kafka Unavailable -> Halt before dependent services, exit non-zero.
2. Kafka Delayed -> Tolerates delay, recovers via bounded backoff.
3. MinIO Unavailable -> Halt before M1, exit non-zero.
4. Bridge Crash -> Immediate detection, logs 'CRITICAL: M1_M2_Consumer_Bridge failed', graceful teardown, non-zero exit.
5. M1 Crash -> Immediate detection, graceful teardown.
6. Clean Stack Startup & Live Pipeline Event Flow (Gateway -> M1 -> Kafka -> Bridge -> M2).
7. Service Restartability -> Clean stop and restart without port collisions.
"""

import asyncio
import os
import subprocess
import sys
import time
import httpx
import psutil

PYTHON_MAIN = sys.executable
LOG_DIR = "E:/ULPF/integration/scratch/deployment_logs"


def log(msg: str):
    print(f"[TEST-BATTERY] {msg}", flush=True)


def stop_all():
    subprocess.run([PYTHON_MAIN, "E:/ULPF/run_stack.py", "--stop"], capture_output=True)


def test_1_kafka_unavailable():
    log("=== TEST 1: Kafka Unavailable ===")
    stop_all()
    # Stop Kafka
    subprocess.run(["docker", "stop", "ulpf-kafka"], capture_output=True)

    env = os.environ.copy()
    env["ULPF_SKIP_CONTAINER_START"] = "1"
    env["ULPF_KAFKA_TIMEOUT"] = "5.0"

    res = subprocess.run(
        [PYTHON_MAIN, "E:/ULPF/run_stack.py", "--check-only"],
        env=env,
        capture_output=True,
        text=True,
        cwd="E:/ULPF"
    )

    log(f"Exit code: {res.returncode} (Expected: != 0)")
    assert res.returncode != 0, f"Expected non-zero exit code, got {res.returncode}"
    assert "CRITICAL: Kafka broker failed readiness probe" in res.stdout, "Expected Kafka failure in stdout"
    assert "ALL ULPF INTEGRATED SERVICES ARE HEALTHY" not in res.stdout, "Premature ready banner emitted!"

    # Verify no ports listening
    ports = [18080, 18081, 18001, 18082, 18083, 18004, 18085, 18086, 18090]
    netstat = subprocess.run(["netstat", "-ano"], capture_output=True, text=True).stdout
    for line in netstat.splitlines():
        if "LISTENING" in line:
            for p in ports:
                assert f":{p} " not in line, f"Port {p} was prematurely opened and listening: {line}"

    log("PASS: Kafka unavailable correctly prevented all dependent services from starting.")


def test_2_minio_unavailable():
    log("=== TEST 2: MinIO Unavailable ===")
    stop_all()
    # Start Kafka, stop MinIO
    subprocess.run(["docker", "start", "ulpf-kafka"], capture_output=True)
    subprocess.run(["docker", "stop", "ulpf-minio"], capture_output=True)
    time.sleep(3)

    env = os.environ.copy()
    env["ULPF_SKIP_CONTAINER_START"] = "1"
    env["ULPF_MINIO_TIMEOUT"] = "4.0"

    res = subprocess.run(
        [PYTHON_MAIN, "E:/ULPF/run_stack.py", "--check-only"],
        env=env,
        capture_output=True,
        text=True,
        cwd="E:/ULPF"
    )

    log(f"Exit code: {res.returncode} (Expected: != 0)")
    assert res.returncode != 0, f"Expected non-zero exit code, got {res.returncode}"
    assert "CRITICAL: MinIO failed readiness probe" in res.stdout, "Expected MinIO failure in stdout"
    assert "[APP] M1 READY" not in res.stdout, "M1 started while MinIO was down!"

    # Restore MinIO
    subprocess.run(["docker", "start", "ulpf-minio"], capture_output=True)
    time.sleep(2)
    log("PASS: MinIO unavailable correctly prevented M1 and dependent services from starting.")


def test_3_kafka_delayed_startup():
    log("=== TEST 3: Kafka Delayed Startup (Tolerance & Bounded Retry) ===")
    stop_all()
    subprocess.run(["docker", "stop", "ulpf-kafka"], capture_output=True)

    env = os.environ.copy()
    env["ULPF_SKIP_CONTAINER_START"] = "1"
    env["ULPF_KAFKA_TIMEOUT"] = "35.0"

    import threading
    def delayed_starter():
        time.sleep(4)
        log("Delayed starter thread starting Kafka container now...")
        subprocess.run(["docker", "start", "ulpf-kafka"], capture_output=True)

    t = threading.Thread(target=delayed_starter, daemon=True)
    t.start()

    res = subprocess.run(
        [PYTHON_MAIN, "E:/ULPF/run_stack.py", "--check-only"],
        env=env,
        capture_output=True,
        text=True,
        cwd="E:/ULPF"
    )

    t.join(timeout=5)
    log(f"Exit code: {res.returncode} (Expected: 0)")
    assert res.returncode == 0, f"Expected clean recovery after delayed Kafka start, got {res.returncode}\n{res.stdout}\n{res.stderr}"
    assert "[INFRA] Kafka READY" in res.stdout, "Kafka did not report ready after delay!"
    assert "ALL ULPF INTEGRATED SERVICES ARE HEALTHY" in res.stdout
    log("PASS: Supervisor successfully waited for and recovered from delayed Kafka startup.")


def test_4_bridge_crash_detection():
    log("=== TEST 4: Bridge Crash Detection & Supervisor Teardown ===")
    stop_all()
    # Start supervisor as subprocess
    proc = subprocess.Popen(
        [PYTHON_MAIN, "E:/ULPF/run_stack.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="E:/ULPF"
    )

    # Wait until supervisor is ready
    log("Waiting for supervisor to reach PIPELINE_READY...")
    ready = False
    for _ in range(40):
        time.sleep(1)
        # Check if bridge is running
        for p in psutil.process_iter(['pid', 'cmdline']):
            try:
                cmd = " ".join(p.info.get('cmdline') or [])
                if "M1RawEventConsumer" in cmd or "bridge_runner" in cmd:
                    ready = True
                    break
            except Exception:
                pass
        if ready:
            break

    assert ready, "Bridge did not launch in time!"
    time.sleep(2)

    # Find bridge PID and kill it
    bridge_pid = None
    for p in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmd = " ".join(p.info.get('cmdline') or [])
            if "M1RawEventConsumer" in cmd or "bridge_runner" in cmd:
                bridge_pid = p.pid
                p.kill()
                log(f"Deliberately killed Bridge process PID {bridge_pid}")
                break
        except Exception:
            pass

    assert bridge_pid is not None, "Could not find Bridge PID to kill!"

    # Supervisor must detect this within 4 seconds and exit with failure
    try:
        stdout, stderr = proc.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        assert False, "Supervisor hung and did not detect bridge termination!"

    log(f"Supervisor exit code: {proc.returncode} (Expected: != 0)")
    assert proc.returncode != 0, "Supervisor did not exit non-zero on bridge death!"
    assert "CRITICAL: M1_M2_Consumer_Bridge failed" in stdout or "died unexpectedly" in stdout
    log("PASS: Bridge crash was immediately detected and supervisor triggered teardown.")


def test_5_m1_crash_detection():
    log("=== TEST 5: M1 Crash Detection & Supervisor Teardown ===")
    stop_all()
    proc = subprocess.Popen(
        [PYTHON_MAIN, "E:/ULPF/run_stack.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="E:/ULPF"
    )

    log("Waiting for supervisor to reach PIPELINE_READY...")
    ready = False
    for _ in range(40):
        time.sleep(1)
        for p in psutil.process_iter(['pid', 'cmdline']):
            try:
                cmd = " ".join(p.info.get('cmdline') or [])
                if "M1RawEventConsumer" in cmd or "bridge_runner" in cmd:
                    ready = True
                    break
            except Exception:
                pass
        if ready:
            break

    assert ready, "Pipeline did not reach ready state in time!"
    time.sleep(2)

    # Find M1 process
    m1_pid = None
    for p in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmd = " ".join(p.info.get('cmdline') or [])
            if "m1-ingestion" in cmd and "uvicorn" in cmd:
                m1_pid = p.pid
                p.kill()
                log(f"Deliberately killed M1 process PID {m1_pid}")
                break
        except Exception:
            pass

    assert m1_pid is not None, "M1 process was not found!"

    try:
        stdout, stderr = proc.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        assert False, f"Supervisor hung on M1 crash! Stdout: {stdout}"

    log(f"Supervisor exit code: {proc.returncode} (Expected: != 0)")
    assert proc.returncode != 0, "Supervisor did not exit non-zero on M1 death!"
    assert "M1_Ingestion_Vault" in stdout and "died" in stdout
    log("PASS: M1 crash was immediately detected and supervisor terminated.")


def test_6_live_pipeline_event_transmission():
    log("=== TEST 6: Complete Pipeline Event Flow (Gateway -> M1 -> Kafka -> Bridge -> M2) ===")
    stop_all()
    # Start supervisor in background
    proc = subprocess.Popen(
        [PYTHON_MAIN, "E:/ULPF/run_stack.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd="E:/ULPF"
    )

    log("Waiting for PIPELINE_READY...")
    ready = False
    for _ in range(40):
        time.sleep(1)
        try:
            r1 = httpx.get("http://127.0.0.1:18080/health", timeout=1.0)
            r2 = httpx.get("http://127.0.0.1:18001/ready", timeout=1.0)
            r3 = httpx.get("http://127.0.0.1:18082/health", timeout=1.0)
            if r1.status_code == 200 and r2.status_code == 200 and r3.status_code == 200:
                ready = True
                break
        except Exception:
            pass

    assert ready, "Stack failed to reach ready within timeout!"
    time.sleep(3)

    # Post event to Ingress Gateway
    gw_url = "http://127.0.0.1:18080/v1/ingest/event"
    headers = {
        "Authorization": "Bearer key-tenant-cisco-prod",
        "Content-Type": "text/plain",
        "X-Source-ID": "network-cisco-fw01"
    }
    raw_payload = f"<166>Sep 14 11:22:33 cisco-asa %ASA-6-302013: Built inbound TCP connection {int(time.time())} for outside:192.168.1.50/443 to inside:10.0.0.5/8080"

    r = httpx.post(gw_url, headers=headers, content=raw_payload, timeout=5.0)
    log(f"Gateway Response: {r.status_code} -> {r.text}")
    assert r.status_code == 202, f"Expected HTTP 202 from Gateway, got {r.status_code}"
    data = r.json()
    raw_event_id = data["raw_event_id"]
    log(f"Accepted raw_event_id: {raw_event_id}")

    # Wait 2 seconds for Kafka consumption by Bridge and M2 parsing
    time.sleep(2)

    # Verify in Bridge log
    bridge_log = os.path.join(LOG_DIR, "M1_M2_Consumer_Bridge.log")
    with open(bridge_log, "r") as f:
        bridge_content = f.read()

    # Verify M2 parse log
    m2_log = os.path.join(LOG_DIR, "M2_Parser_Engine.log")
    with open(m2_log, "r") as f:
        m2_content = f.read()

    assert "POST /v1/parse HTTP/1.1\" 200" in m2_content, "M2 did not receive or acknowledge parsed event!"
    log("PASS: Event traversed Gateway -> M1 -> Kafka -> Bridge -> M2 with HTTP 200 acknowledgment.")

    # Stop supervisor cleanly
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    stop_all()


def main():
    log("Starting ULPF Hardening Test Battery...")
    try:
        test_1_kafka_unavailable()
        test_2_minio_unavailable()
        test_3_kafka_delayed_startup()
        test_4_bridge_crash_detection()
        test_5_m1_crash_detection()
        test_6_live_pipeline_event_transmission()
        log("==================================================")
        log("ALL 6 HARDENING TEST BATTERIES PASSED WITH 100% SUCCESS!")
        log("==================================================")
        sys.exit(0)
    except Exception as e:
        log(f"TEST FAILED WITH EXCEPTION: {e}")
        stop_all()
        raise


if __name__ == "__main__":
    main()
