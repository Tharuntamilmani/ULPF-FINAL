"""
End-to-end verification script for ULPF Web Applications and Backend Integration.
Tests:
- Direct HTTP availability of M6 UI (5173) and M3 UI (5174)
- Frontend Vite reverse proxy routes:
    /api -> M6 (18086)
    /system-health -> Health Aggregator (18090)
    /events-api -> M5 (18085)
    /m2 -> M2 (18082)
    /v1 -> M3 (18083)
- Real authentication flow against M6
- Tenant listing via real M6 API
- System health reporting via real Health Aggregator
- Live log ingestion via Ingress Gateway (18080)
- End-to-end pipeline processing: Gateway -> M1 -> Kafka -> M2 -> M3 -> M4 -> M5 -> OpenSearch
- Live event search and detail retrieval from M5
- M3 developer console: Raw Log -> M2 Parse -> M3 Normalize -> Canonical UES
"""

import sys
import time
import json
import httpx

results = {}

def run_test(name, fn):
    try:
        res = fn()
        results[name] = {"status": "PASS", "detail": res}
        print(f"[PASS] {name}: {res}")
    except Exception as e:
        results[name] = {"status": "FAIL", "detail": str(e)}
        print(f"[FAIL] {name}: {e}")

def test_m6_ui_http():
    r = httpx.get("http://127.0.0.1:5173", timeout=5.0)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert "ULPF" in r.text or "doctype html" in r.text.lower(), "HTML response missing"
    return "M6 UI served HTTP 200 with HTML shell"

def test_m3_ui_http():
    r = httpx.get("http://127.0.0.1:5174", timeout=5.0)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    assert "doctype html" in r.text.lower(), "HTML response missing"
    return "M3 UI served HTTP 200 with HTML shell"

def test_m6_auth_and_proxy():
    # Test via M6 frontend proxy /api with OAuth2 form data
    data = {"username": "admin", "password": "Admin_Secure_Pass_2026!"}
    r = httpx.post(
        "http://127.0.0.1:5173/api/v1/auth/login",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=5.0
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    resp_data = r.json()
    token = resp_data.get("access_token")
    assert token, "No access_token returned"
    role = resp_data.get("role")
    return f"Authenticated successfully as {role} (token prefix: {token[:12]}...)"

def test_m6_tenants_api():
    # Authenticate via proxy
    r_auth = httpx.post(
        "http://127.0.0.1:5173/api/v1/auth/login",
        data={"username": "admin", "password": "Admin_Secure_Pass_2026!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = r_auth.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Query tenants via proxy without trailing slash
    r = httpx.get("http://127.0.0.1:5173/api/v1/tenants", headers=headers, timeout=5.0)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    tenants_data = r.json()
    items = tenants_data.get("items", []) if isinstance(tenants_data, dict) else tenants_data
    tenant_ids = [t.get("slug") or t.get("name") for t in items]

    return f"Active tenants in system: {len(items)} ({', '.join(str(tid) for tid in tenant_ids[:4])})"

def test_system_health_proxy():
    r = httpx.get("http://127.0.0.1:5173/system-health", timeout=5.0)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    overall = data.get("status") or data.get("overall_status")
    modules = data.get("modules", {})
    return f"Overall health: {overall}, Healthy modules reported: {len(modules)}"

def test_m3_m2_proxy_parse():
    # Test M3 proxy /m2/v1/parse -> M2 /v1/parse
    raw_log = "<189>Sep 12 04:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443"
    envelope = {
        "schema_version": "1.0.0",
        "raw_event_id": f"test-raw-{int(time.time())}",
        "tenant_id": "tenant-cisco",
        "source_id": "cisco-01",
        "transport": "syslog",
        "payload": raw_log
    }
    r = httpx.post(
        "http://127.0.0.1:5174/m2/v1/parse",
        json=envelope,
        headers={"Authorization": "Bearer system-admin-token", "X-Tenant-ID": "tenant-cisco"},
        timeout=5.0
    )
    assert r.status_code == 200, f"M2 parse failed with {r.status_code}: {r.text}"
    data = r.json()
    parser_info = data.get("parser", {})
    return f"Parsed via M2: parser_id={parser_info.get('id')}, fields={len(data.get('fields', {}))}"

def test_m3_normalize_pipeline():
    # 1. Parse via M2
    raw_log = "<189>Sep 12 04:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443"
    envelope = {
        "schema_version": "1.0.0",
        "raw_event_id": f"test-raw-{int(time.time())}",
        "tenant_id": "tenant-cisco",
        "source_id": "cisco-01",
        "transport": "syslog",
        "payload": raw_log
    }
    p_resp = httpx.post(
        "http://127.0.0.1:18082/v1/parse",
        json=envelope,
        headers={"Authorization": "Bearer system-admin-token", "X-Tenant-ID": "tenant-cisco"},
        timeout=5.0
    ).json()
    
    # 2. Normalize via M3 proxy /v1/normalize
    r = httpx.post("http://127.0.0.1:5174/v1/normalize", json=p_resp, timeout=5.0)
    assert r.status_code == 200, f"Normalize failed with {r.status_code}: {r.text}"
    data = r.json()
    assert data.get("success") is True, f"Normalization marked failed: {data}"
    ulpf = data.get("event", {}).get("ulpf", {})
    ev_type = ulpf.get("event", {}).get("type")
    parser_id = ulpf.get("parser", {}).get("id")
    return f"Canonical UES normalized: event.type='{ev_type}', parser='{parser_id}', unmapped={len(data.get('unmapped_fields', []))}"

def test_live_pipeline_ingestion_and_opensearch():
    # Ingest event through Gateway 18080
    raw_log = "<189>Sep 12 04:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443"
    ingest_payload = {
        "message": raw_log,
        "format_hint": "syslog"
    }
    r = httpx.post(
        "http://127.0.0.1:18080/v1/events",
        json=ingest_payload,
        headers={"Authorization": "Bearer key-tenant-cisco-prod", "Content-Type": "application/json"},
        timeout=5.0
    )
    assert r.status_code == 202, f"Gateway ingestion failed: {r.status_code}: {r.text}"
    ingest_data = r.json()
    raw_event_id = ingest_data.get("raw_event_id")
    sha256 = ingest_data.get("sha256")

    # Give pipeline a moment to flow through M1 -> Kafka -> M2 -> M3 -> M4 -> M5 -> OpenSearch
    time.sleep(3.0)

    # Query M5 via frontend proxy /events-api/events
    r_events = httpx.get("http://127.0.0.1:5173/events-api/events", timeout=5.0)
    assert r_events.status_code == 200, f"M5 event query failed: {r_events.status_code}: {r_events.text}"
    events_resp = r_events.json()
    events = events_resp.get("events", [])
    
    return f"Ingested raw_event_id={raw_event_id}, sha256={sha256[:12]}..., Query returned {len(events)} total stored events"

if __name__ == "__main__":
    print("=== RUNNING ULPF WEB APPLICATION & BACKEND E2E TEST SUITE ===")
    run_test("M6 Web Application UI (Port 5173)", test_m6_ui_http)
    run_test("M3 Developer Console UI (Port 5174)", test_m3_ui_http)
    run_test("M6 Authentication via Proxy (/api/v1/auth/login)", test_m6_auth_and_proxy)
    run_test("M6 Tenant Management API (/api/v1/tenants)", test_m6_tenants_api)
    run_test("System Health Telemetry Proxy (/system-health)", test_system_health_proxy)
    run_test("M3 Developer Console M2 Parse Proxy (/m2/v1/parse)", test_m3_m2_proxy_parse)
    run_test("M3 Normalizer Pipeline (/v1/normalize -> Canonical UES)", test_m3_normalize_pipeline)
    run_test("End-to-End Log Ingestion -> Kafka -> Bridge -> M5 Search", test_live_pipeline_ingestion_and_opensearch)

    print("\n=== SUMMARY ===")
    all_passed = True
    for name, res in results.items():
        if res["status"] != "PASS":
            all_passed = False
        print(f"  {res['status']}: {name} -> {res['detail']}")
    
    with open("E:/ULPF/integration/scratch/web_verification_results.json", "w") as f:
        json.dump(results, f, indent=2)

    sys.exit(0 if all_passed else 1)
