import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.registry.repository import ParserRepository
from app.registry.service import ParserRegistryService
from app.registry.models import ParserDefinition, ParserStatus
from app.classifier.detector import ClassificationResult

client = TestClient(app)


def test_tenant_isolation_adversarial_matrix():
    repo = ParserRepository()
    service = ParserRegistryService(repo)

    # 1. Tenant A registers a custom parser for "AcmeApp"
    p_a = ParserDefinition(
        id="parser-acme-app",
        name="Acme App Parser (Tenant A)",
        tenant_id="tenant-a",
        vendor="Acme",
        product="App",
        formats=["syslog"],
        version="1.0.0",
        patterns=["^ACME_AUTH user=%{WORD:user} ip=%{IP:srcip}"],
    )
    service.register_parser(p_a, caller_tenant_id="tenant-a")

    # 2. Tenant B registers a different custom parser with the SAME id or vendor for Tenant B
    p_b = ParserDefinition(
        id="parser-acme-app",
        name="Acme App Parser (Tenant B)",
        tenant_id="tenant-b",
        vendor="Acme",
        product="App",
        formats=["syslog"],
        version="1.0.0",
        patterns=["^ACME_AUTH user_id=%{INT:user_id} client=%{IP:srcip}"],
    )
    service.register_parser(p_b, caller_tenant_id="tenant-b")

    # Prove Tenant A CANNOT register under Tenant B
    with pytest.raises(ValueError, match="Forbidden"):
        p_rogue = ParserDefinition(
            id="parser-rogue",
            name="Rogue Parser",
            tenant_id="tenant-b",
            vendor="Acme",
            product="App",
            formats=["syslog"],
            version="1.0.0",
            patterns=["^.*"],
        )
        service.register_parser(p_rogue, caller_tenant_id="tenant-a")

    # Prove Tenant A CANNOT register global baseline parser
    with pytest.raises(
        ValueError, match="Non-system callers cannot register global baseline parsers"
    ):
        p_global = ParserDefinition(
            id="parser-rogue-global",
            name="Rogue Global",
            tenant_id="global",
            vendor="Acme",
            product="App",
            formats=["syslog"],
            version="1.0.0",
            patterns=["^.*"],
        )
        service.register_parser(p_global, caller_tenant_id="tenant-a")

    # Prove Tenant A lists ONLY Tenant A parsers (+ global baseline)
    tenant_a_parsers = repo.list_for_tenant(tenant_id="tenant-a", include_global=False)
    assert len(tenant_a_parsers) == 1
    assert tenant_a_parsers[0].name == "Acme App Parser (Tenant A)"

    # Prove Tenant B lists ONLY Tenant B parsers (+ global baseline)
    tenant_b_parsers = repo.list_for_tenant(tenant_id="tenant-b", include_global=False)
    assert len(tenant_b_parsers) == 1
    assert tenant_b_parsers[0].name == "Acme App Parser (Tenant B)"

    # Prove Tenant A resolution binds Tenant A parser
    classif = ClassificationResult(
        format="syslog", vendor="Acme", product="App", confidence=0.95
    )
    env_a = {"payload": "ACME_AUTH user=alice ip=10.0.0.1"}
    exec_a, defn_a = service.find_parser(classif, env_a, tenant_id="tenant-a")
    assert defn_a is not None
    assert defn_a.tenant_id == "tenant-a"
    extracted_a = exec_a.parse(env_a)
    assert extracted_a["user"] == "alice"

    # Prove Tenant B resolution binds Tenant B parser, NOT Tenant A
    env_b = {"payload": "ACME_AUTH user_id=12345 client=192.168.1.1"}
    exec_b, defn_b = service.find_parser(classif, env_b, tenant_id="tenant-b")
    assert defn_b is not None
    assert defn_b.tenant_id == "tenant-b"
    extracted_b = exec_b.parse(env_b)
    assert extracted_b["user_id"] == 12345

    # Prove Tenant A CANNOT disable Tenant B parser
    # Calling disable for parser under tenant-a will only affect tenant-a's definition
    success = service.disable_parser("parser-acme-app", tenant_id="tenant-a")
    assert success is True
    # Verify Tenant A parser is disabled
    assert (
        repo.get("parser-acme-app", tenant_id="tenant-a").status
        == ParserStatus.DISABLED
    )
    # Verify Tenant B parser remains ACTIVE and untouched
    assert (
        repo.get("parser-acme-app", tenant_id="tenant-b").status == ParserStatus.ACTIVE
    )


def test_api_tenant_spoofing_adversarial():
    # Setup Tenant B parser via API using Tenant B admin credentials
    p_b = {
        "id": "parser-secret-tenant-b",
        "name": "Tenant B Secret Parser",
        "tenant_id": "tenant-b",
        "vendor": "SecretVendor",
        "product": "SecretProduct",
        "formats": ["syslog"],
        "version": "1.0.0",
        "patterns": ["^SECRET token=%{WORD:token}"],
    }
    res_b = client.post(
        "/v1/parsers/register", json=p_b, headers={"X-API-Key": "tenant-b-admin-key"}
    )
    assert res_b.status_code == 200

    # Test 1: Tenant A CANNOT see Tenant B parser in GET /v1/parsers
    res_list = client.get("/v1/parsers", headers={"X-API-Key": "tenant-a-admin-key"})
    assert res_list.status_code == 200
    listed_ids = [p["id"] for p in res_list.json()]
    assert "parser-secret-tenant-b" not in listed_ids

    # Test 2: Tenant A CANNOT fetch Tenant B parser in GET /v1/parsers/{id}
    res_get = client.get(
        "/v1/parsers/parser-secret-tenant-b",
        headers={"X-API-Key": "tenant-a-admin-key"},
    )
    assert res_get.status_code == 404

    # Test 3: Tenant A CANNOT disable Tenant B parser
    res_dis = client.post(
        "/v1/parsers/parser-secret-tenant-b/disable",
        headers={"X-API-Key": "tenant-a-admin-key"},
    )
    assert res_dis.status_code == 404

    # Test 4: Tenant A CANNOT execute Tenant B parser via ingestion spoofing
    spoofed_event = {
        "raw_event_id": "spoof_001",
        "tenant_id": "tenant-b",
        "payload": "SECRET token=classified_xyz",
    }
    # Using Tenant A credentials with Tenant B body
    res_spoof = client.post(
        "/v1/parse", json=spoofed_event, headers={"X-API-Key": "tenant-a-ingest-key"}
    )
    assert res_spoof.status_code == 403
    assert "cannot ingest for" in res_spoof.json()["detail"]

    # Test 5: Tenant A submitting legitimate Tenant A event with Tenant B secret payload falls back to UNPARSED
    legit_a_event = {
        "raw_event_id": "legit_a_001",
        "tenant_id": "tenant-a",
        "payload": "SECRET token=classified_xyz",
    }
    res_legit = client.post(
        "/v1/parse", json=legit_a_event, headers={"X-API-Key": "tenant-a-ingest-key"}
    )
    assert res_legit.status_code == 200
    # Must NOT execute Tenant B's parser!
    assert res_legit.json()["status"] == "UNPARSED"
    assert res_legit.json()["parser"]["id"] != "parser-secret-tenant-b"
