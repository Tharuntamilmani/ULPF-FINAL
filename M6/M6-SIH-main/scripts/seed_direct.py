"""
Direct psycopg2 seed script — no asyncio, no asyncpg.
Inserts all bootstrap data using synchronous psycopg2.
"""
from __future__ import annotations
import os, sys, json, uuid
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

host = os.environ.get("POSTGRES_HOST", "postgres")
port = os.environ.get("POSTGRES_PORT", "5432")
db   = os.environ.get("POSTGRES_DB",   "m6_control_plane")
user = os.environ.get("POSTGRES_USER", "m6user")
pwd  = os.environ.get("POSTGRES_PASSWORD", "")

# bcrypt hash of "Admin@SIH2026!"
ADMIN_HASH = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"

# Generate bcrypt hash directly
try:
    import bcrypt as _bcrypt
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@SIH2026!")
    pwd_bytes = admin_password.encode("utf-8")[:72]  # bcrypt 72-byte limit
    ADMIN_HASH = _bcrypt.hashpw(pwd_bytes, _bcrypt.gensalt(rounds=12)).decode("utf-8")
    print(f"  Generated bcrypt hash for admin password.")
except Exception as e:
    print(f"  Warning: could not generate hash ({e}), using pre-computed hash")

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc)

print("\n=== ULPF M6 Seed Script (direct psycopg2) ===\n")
print(f"Connecting to {host}:{port}/{db}...")

conn = psycopg2.connect(host=host, port=port, dbname=db, user=user, password=pwd)
conn.autocommit = False
cur = conn.cursor()

# ── Roles ──────────────────────────────────────────────────────────────────────
ROLES = [
    ("ADMINISTRATOR",    "Full control over M6 control plane"),
    ("PARSER_DEVELOPER", "Parser and mapping management"),
    ("SECURITY_ANALYST", "View services, configs, and dashboards"),
    ("VIEWER",           "Read-only access"),
]
role_ids = {}
for name, desc in ROLES:
    cur.execute("SELECT id FROM roles WHERE name = %s", (name,))
    row = cur.fetchone()
    if row:
        role_ids[name] = row[0]
        print(f"  Role exists: {name}")
    else:
        rid = uid()
        cur.execute(
            "INSERT INTO roles(id, name, description, created_at, updated_at) VALUES(%s,%s,%s,%s,%s)",
            (rid, name, desc, now(), now())
        )
        role_ids[name] = rid
        print(f"  Role created: {name}")

# ── Admin user ─────────────────────────────────────────────────────────────────
admin_user = os.environ.get("ADMIN_USERNAME", "admin")
admin_email = os.environ.get("ADMIN_EMAIL", "admin@ulpf.local")

cur.execute("SELECT id FROM users WHERE username = %s", (admin_user,))
row = cur.fetchone()
if row:
    admin_id = row[0]
    print(f"  Admin user exists: {admin_user}")
else:
    admin_id = uid()
    cur.execute(
        "INSERT INTO users(id,username,email,hashed_password,is_active,is_superuser,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
        (admin_id, admin_user, admin_email, ADMIN_HASH, True, True, now(), now())
    )
    cur.execute(
        "INSERT INTO user_roles(user_id, role_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",
        (admin_id, role_ids["ADMINISTRATOR"])
    )
    print(f"  Admin user created: {admin_user}")

# ── Sources ────────────────────────────────────────────────────────────────────
SOURCES = [
    ("cisco-asa-fw-01",  "Edge Firewall (Cisco ASA)", "Cisco",                "ASA",           "firewall", "syslog", "udp", 514,  "dmz",      "demo-tenant", "parser-cisco-asa"),
    ("paloalto-ngfw-01", "Core NGFW (Palo Alto)",     "Palo Alto Networks",   "PAN-OS",        "firewall", "syslog", "tcp", 514,  "core",     "demo-tenant", "parser-paloalto"),
    ("windows-dc-01",    "Domain Controller",          "Microsoft",            "Windows Server","server",   "winrm",  "tcp", 5985, "internal", "demo-tenant", "parser-windows"),
    ("linux-web-01",     "Web Server (Linux)",         "Linux",                "Ubuntu 22.04",  "server",   "syslog", "udp", 514,  "dmz",      "demo-tenant", "parser-linux"),
]
for src_id, name, vendor, product, stype, proto, transport, port_num, zone, tenant, parser_id in SOURCES:
    cur.execute("SELECT id FROM sources WHERE source_id = %s", (src_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO sources(id,source_id,tenant_id,name,vendor,product,source_type,protocol,transport,port,zone,status,parser_id,created_by,updated_by,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (uid(), src_id, tenant, name, vendor, product, stype, proto, transport, port_num, zone, "active".upper(), parser_id, admin_user, admin_user, now(), now())
        )
        print(f"  Source created: {src_id}")

# ── Parsers ────────────────────────────────────────────────────────────────────
PARSERS = [
    ("parser-cisco-asa",    "Cisco ASA Parser",             "Cisco",               "ASA",           "syslog", "1.0.0", "ACTIVE"),
    ("parser-paloalto",     "Palo Alto PAN-OS Parser",      "Palo Alto Networks",  "PAN-OS",        "syslog", "1.0.0", "ACTIVE"),
    ("parser-windows",      "Windows Event Log Parser",     "Microsoft",           "Windows",       "evtx",   "1.0.0", "ACTIVE"),
    ("parser-linux",        "Linux Syslog Parser",          "Linux",               "Syslog",        "syslog", "1.0.0", "ACTIVE"),
    ("parser-cisco-asa-v2", "Cisco ASA Parser v2 (Draft)", "Cisco",               "ASA",           "syslog", "2.0.0", "DRAFT"),
]
for p_id, name, vendor, product, fmt, ver, status in PARSERS:
    cur.execute("SELECT id FROM parsers WHERE parser_id = %s", (p_id,))
    if not cur.fetchone():
        approved_by = admin_user if status == "ACTIVE" else None
        cur.execute(
            "INSERT INTO parsers(id,parser_id,name,vendor,product,format,version,status,created_by,updated_by,approved_by,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (uid(), p_id, name, vendor, product, fmt, ver, status, admin_user, admin_user, approved_by, now(), now())
        )
        print(f"  Parser created: {p_id} ({status})")

# ── Schema: UES ────────────────────────────────────────────────────────────────
cur.execute("SELECT id FROM schemas WHERE name = 'ues'")
row = cur.fetchone()
if not row:
    schema_id = uid()
    cur.execute(
        "INSERT INTO schemas(id,name,description,created_by,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s)",
        (schema_id, "ues", "Universal Event Schema", admin_user, now(), now())
    )
    ues_schema = {
        "$id": "ulpf:ues:v1.0.0", "title": "UniversalEventSchema", "type": "object",
        "required": ["event_id","tenant_id","timestamp","event"],
        "properties": {
            "event_id": {"type":"string"}, "tenant_id": {"type":"string"},
            "timestamp": {"type":"string"}, "event": {"type":"object"},
            "source": {"type":"object"}, "destination": {"type":"object"},
        }
    }
    cur.execute(
        "INSERT INTO schema_versions(id,schema_id,version,status,json_schema,created_by,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
        (uid(), schema_id, "1.0.0", "active", json.dumps(ues_schema), admin_user, now(), now())
    )
    print("  Schema created: ues v1.0.0")

# ── Mappings ───────────────────────────────────────────────────────────────────
MAPPINGS = [
    ("cisco-asa-ues-v1", "Cisco ASA → UES v1.0.0", "cisco-asa", "ues", "1.0.0",
     {"srcip":"source.ip","dstip":"destination.ip","srcport":"source.port","dstport":"destination.port","action":"event.action"}),
    ("paloalto-ues-v1",  "Palo Alto → UES v1.0.0",  "pan-os",    "ues", "1.0.0",
     {"src":"source.ip","dst":"destination.ip","sport":"source.port","dport":"destination.port","action":"event.action"}),
]
for m_id, name, src_fmt, tgt_schema, tgt_ver, fields in MAPPINGS:
    cur.execute("SELECT id FROM mappings WHERE mapping_id = %s", (m_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO mappings(id,mapping_id,name,source_format,target_schema,target_version,version,fields,is_active,created_by,updated_by,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (uid(), m_id, name, src_fmt, tgt_schema, tgt_ver, "1.0.0", json.dumps(fields), True, admin_user, admin_user, now(), now())
        )
        print(f"  Mapping created: {m_id}")

# ── Policies ───────────────────────────────────────────────────────────────────
POLICIES = [
    ("critical-security", "Critical Security Events", 100, True,
     [{"field":"event.severity.value","operator":">=","value":7},{"field":"security.is_security_event","operator":"==","value":True}],
     ["siem","data_lake","ai_stream"]),
    ("high-severity",     "High Severity Events",     80,  True,
     [{"field":"event.severity.value","operator":">=","value":5}],
     ["siem","data_lake"]),
    ("default-data-lake", "Default Data Lake",         1,  True, [], ["data_lake"]),
]
for p_id, name, priority, enabled, conditions, destinations in POLICIES:
    cur.execute("SELECT id FROM policies WHERE policy_id = %s", (p_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO policies(id,policy_id,name,version,priority,conditions,destinations,is_enabled,created_by,updated_by,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (uid(), p_id, name, "1.0.0", priority, json.dumps(conditions), json.dumps(destinations), enabled, admin_user, admin_user, now(), now())
        )
        print(f"  Policy created: {p_id}")

# ── Services ───────────────────────────────────────────────────────────────────
SERVICES = [
    ("m1-ingestion",  "M1 Ingestion Service",  "module", False),
    ("m2-parser",     "M2 Parser Service",      "module", False),
    ("m3-normalizer", "M3 Normalizer Service",  "module", False),
    ("m4-enrichment", "M4 Enrichment Service",  "module", False),
    ("m5-delivery",   "M5 SIEM Delivery",       "module", False),
    ("kafka",         "Apache Kafka",           "infra",  True),
    ("minio",         "MinIO Object Storage",   "infra",  False),
    ("opensearch",    "OpenSearch",             "infra",  False),
    ("postgres",      "PostgreSQL",             "infra",  True),
    ("redis",         "Redis",                  "infra",  True),
    ("prometheus",    "Prometheus",             "infra",  False),
    ("grafana",       "Grafana",                "infra",  False),
]
for key, name, stype, critical in SERVICES:
    cur.execute("SELECT id FROM services WHERE service_key = %s", (key,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO services(id,service_key,name,service_type,is_critical,last_status,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
            (uid(), key, name, stype, critical, "UNKNOWN", now(), now())
        )
        print(f"  Service registered: {key}")

conn.commit()
cur.close()
conn.close()
print("\nSeed complete. M6 bootstrap data is ready!")
