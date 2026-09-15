"""
ULPF Member 2 — End-to-End Demonstration Script
Demonstrates Known Ingestion, Unknown-Source Discovery, Parser Studio Onboarding,
Parser Versioning, and Historical Event Replay.
"""

import json
import time
from app.models.envelope import RawEventEnvelope
from app.classifier.detector import Classifier
from app.registry.repository import ParserRepository
from app.registry.service import ParserRegistryService
from app.registry.models import ParserDefinition, ParserStatus
from app.discovery import UnknownSourceDiscoveryEngine
from app.studio import ParserValidator, MappingBuilder, StudioTestRunner
from app.replay import ReplayService

def print_section(title: str):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def run_demo():
    print_section("DEMO STEP 1: INITIALIZE M2 COMPONENT REGISTRY & CLASSIFIER")
    repo = ParserRepository()
    repo.load_from_directory("./parsers")
    registry_service = ParserRegistryService(repo)
    classifier = Classifier()
    discovery_engine = UnknownSourceDiscoveryEngine()
    replay_service = ReplayService(registry_service, classifier)

    active_parsers = repo.list_all()
    print(f"Loaded {len(active_parsers)} parsers into registry:")
    for p in active_parsers:
        print(f"  - [{p.id}] {p.name} (v{p.version}) - {p.vendor} {p.product} ({', '.join(p.formats)})")

    # ---------------------------------------------------------
    print_section("DEMO STEP 2: KNOWN SOURCE INGESTION (Cisco ASA Syslog)")
    # ---------------------------------------------------------
    cisco_raw = RawEventEnvelope(
        raw_event_id="raw_cisco_001",
        payload="<189>Sep 12 04:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443"
    )
    print(f"Input RawEventEnvelope payload:\n  '{cisco_raw.payload}'")

    # Classification
    classification = classifier.classify(cisco_raw)
    print(f"\nClassification Result:")
    print(f"  Format:     {classification.format}")
    print(f"  Vendor:     {classification.vendor}")
    print(f"  Product:    {classification.product}")
    print(f"  Confidence: {classification.confidence}")

    # Parser Execution
    executable, defn = registry_service.find_parser(classification, cisco_raw.model_dump())
    extracted = executable.parse(cisco_raw.model_dump())
    print(f"\nMatched Parser: [{defn.id}] v{defn.version}")
    print("Extracted Source-Specific Fields (M2 Output -> M3):")
    print(json.dumps(extracted, indent=4))

    # ---------------------------------------------------------
    print_section("DEMO STEP 3: UNKNOWN SOURCE DISCOVERY")
    # ---------------------------------------------------------
    unknown_raw = RawEventEnvelope(
        raw_event_id="raw_unknown_999",
        payload="device=ACME-FW-01 src_addr=10.0.0.5 dst_addr=8.8.8.8 src_prt=51234 dst_prt=443 decision=permit"
    )
    print(f"Incoming Unknown Raw Event:\n  '{unknown_raw.payload}'")

    # Attempt lookup (no custom ACME parser exists)
    unknown_class = classifier.classify(unknown_raw)
    exec_p, defn_p = registry_service.find_parser(unknown_class, unknown_raw.model_dump())
    print(f"\nClassifier Result: Format='{unknown_class.format}', Vendor='{unknown_class.vendor}'")
    
    # Run Discovery Engine
    discovery_res = discovery_engine.discover(unknown_raw.payload)
    print("\nDiscovery Engine Analysis:")
    print(f"  Candidate Format: {discovery_res['discovery']['format']}")
    print(f"  Discovery Score:  {discovery_res['discovery']['confidence']}")
    print("  Detected Fields:  ", list(discovery_res['detected_fields'].keys()))
    print("  Suggested Target Mappings:")
    for k, v in discovery_res['suggestions'].items():
        print(f"    {k:15s} ------> {v}")

    # ---------------------------------------------------------
    print_section("DEMO STEP 4: PARSER STUDIO — TEST & REGISTER NEW ACME PARSER")
    # ---------------------------------------------------------
    acme_defn = ParserDefinition(
        id="parser-acme-firewall",
        name="ACME Next-Gen Firewall Parser",
        vendor="ACME",
        product="Firewall",
        formats=["kv"],
        version="1.0.0",
        mapping_version="1.0.0",
        priority=20,
        patterns=[
            "device=%{NOTSPACE:device}\\s+src_addr=%{IP:src_addr}\\s+dst_addr=%{IP:dst_addr}\\s+src_prt=%{INT:src_prt}\\s+dst_prt=%{INT:dst_prt}\\s+decision=%{NOTSPACE:decision}"
        ],
        fields={
            "src_addr": "src_addr",
            "dst_addr": "dst_addr",
            "src_prt": "src_prt",
            "dst_prt": "dst_prt",
            "decision": "decision"
        }
    )

    # Validate
    valid, errors = ParserValidator.validate_parser_config(acme_defn.model_dump())
    print(f"Validation Status: {'PASS' if valid else 'FAIL'}")

    # Studio Test Dry-Run
    test_runner = StudioTestRunner(registry_service)
    test_results = test_runner.test_parser(acme_defn, [unknown_raw.payload])
    print(f"Studio Test Extraction Result:")
    print(json.dumps(test_results[0]["extracted_fields"], indent=4))

    # Register
    registry_service.register_parser(acme_defn)
    print(f"Successfully registered parser '{acme_defn.id}' v{acme_defn.version}!")

    # ---------------------------------------------------------
    print_section("DEMO STEP 5: REPLAY HISTORICAL UNKNOWN RAW EVENTS")
    # ---------------------------------------------------------
    historical_events = [
        RawEventEnvelope(raw_event_id="raw_hist_001", payload="device=ACME-FW-01 src_addr=10.0.0.5 dst_addr=8.8.8.8 src_prt=51234 dst_prt=443 decision=permit"),
        RawEventEnvelope(raw_event_id="raw_hist_002", payload="device=ACME-FW-01 src_addr=192.168.1.50 dst_addr=1.1.1.1 src_prt=61200 dst_prt=80 decision=deny")
    ]

    replayed = replay_service.replay_events("parser-acme-firewall", historical_events, version="1.0.0")
    print(f"Replayed {len(replayed)} raw historical events through newly registered parser:")
    for pe in replayed:
        print(f"  Event ID: {pe.raw_event_id} | Parser: {pe.parser.id}:{pe.parser.version} | Processing Time: {pe.processing_time_ms}ms")
        print(f"  Extracted: {pe.fields}")

    # ---------------------------------------------------------
    print_section("DEMO STEP 6: PARSER VERSIONING & ROLLBACK")
    # ---------------------------------------------------------
    acme_v11 = ParserDefinition(
        id="parser-acme-firewall",
        name="ACME Next-Gen Firewall Parser v1.1",
        vendor="ACME",
        product="Firewall",
        formats=["kv"],
        version="1.1.0",
        mapping_version="1.1.0",
        priority=20,
        patterns=[acme_defn.patterns[0]],
        fields=acme_defn.fields
    )
    registry_service.register_parser(acme_v11)
    print(f"Registered updated version 1.1.0. Active version is now: {repo.get('parser-acme-firewall').version}")

    # Rollback to 1.0.0
    rolled_back = registry_service.rollback_parser("parser-acme-firewall", "1.0.0")
    print(f"Rolled back 'parser-acme-firewall' to version: {rolled_back.version}")

    print_section("M2 DEMONSTRATION COMPLETE — DEFINITION OF DONE VERIFIED")

if __name__ == "__main__":
    run_demo()
