import httpx
import json

results = {}

# 1. Check Frontends
for port, name in [(5173, 'M6 Control Plane UI'), (5174, 'M3 Normalizer Console')]:
    try:
        r = httpx.get(f'http://127.0.0.1:{port}', timeout=3.0)
        results[name] = f'UP (HTTP {r.status_code})'
    except Exception as e:
        results[name] = f'DOWN ({e})'

# 2. Check Health Aggregator
try:
    r = httpx.get('http://127.0.0.1:18090/health', timeout=3.0)
    data = r.json()
    status_str = data.get('status')
    mod_count = len(data.get('modules', {}))
    results['Health Aggregator (18090)'] = f'{status_str} ({mod_count} modules healthy)'
    for mod, details in data.get('modules', {}).items():
        is_h = details.get('healthy')
        lat = details.get('latency_ms')
        results[f'Module {mod}'] = f'Healthy: {is_h} ({lat} ms)'
except Exception as e:
    results['Health Aggregator'] = f'DOWN ({e})'

# 3. Check M6 Login & Tenants via UI proxy (5173)
try:
    r_auth = httpx.post(
        'http://127.0.0.1:5173/api/v1/auth/login',
        data={'username': 'admin', 'password': 'Admin_Secure_Pass_2026!'},
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=3.0
    )
    token = r_auth.json().get('access_token')
    role = r_auth.json().get('role')
    results['M6 Auth API (via 5173)'] = f'SUCCESS (Role: {role})'
    r_tenants = httpx.get('http://127.0.0.1:5173/api/v1/tenants', headers={'Authorization': f'Bearer {token}'}, timeout=3.0)
    items = r_tenants.json().get('items', [])
    results['M6 Tenants API (via 5173)'] = f'SUCCESS ({len(items)} active tenants)'
except Exception as e:
    results['M6 API'] = f'FAIL ({e})'

# 4. Check M3 Parse & Normalize via UI proxy (5174)
try:
    raw_log = '<189>Sep 12 04:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443'
    p_resp = httpx.post(
        'http://127.0.0.1:5174/m2/v1/parse',
        json={'raw_event_id': 'live-chk-1', 'payload': raw_log, 'tenant_id': 'tenant-cisco', 'source_id': 'cisco-01', 'transport': 'syslog'},
        headers={'Authorization': 'Bearer system-admin-token', 'X-Tenant-ID': 'tenant-cisco'},
        timeout=3.0
    ).json()
    norm_resp = httpx.post('http://127.0.0.1:5174/v1/normalize', json=p_resp, timeout=3.0).json()
    ev_type = norm_resp.get('event', {}).get('ulpf', {}).get('event', {}).get('type')
    results['M3 Parse & Normalize Pipeline (via 5174)'] = f'SUCCESS (Parsed: {p_resp.get("status")}, Canonical UES event.type: {ev_type})'
except Exception as e:
    results['M3 Pipeline'] = f'FAIL ({e})'

print(json.dumps(results, indent=2))
