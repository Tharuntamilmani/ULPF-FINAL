"""
Isolated Module Loader for ULPF Integration Testing.

Allows contract tests, E2E tests, and security tests to import and execute
REAL M1, M2, M3, M4, M5, and M6 code without colliding on their shared 'app' package name.
"""

import os
import sys
import types
import importlib.util
from typing import Any

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def bind_package(pkg_name: str, pkg_dir: str) -> Any:
    """Register package in sys.modules so relative and package imports work properly."""
    init_path = os.path.join(pkg_dir, "__init__.py")
    if os.path.exists(init_path):
        spec = importlib.util.spec_from_file_location(pkg_name, init_path)
        if spec and spec.loader:
            pkg = importlib.util.module_from_spec(spec)
            sys.modules[pkg_name] = pkg
            spec.loader.exec_module(pkg)
            return pkg
    
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [pkg_dir]
    pkg.__file__ = init_path
    sys.modules[pkg_name] = pkg
    return pkg


def load_mod(mod_name: str, file_path: str) -> Any:
    """Load module from path and bind into sys.modules."""
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, file_path)
    if not spec or not spec.loader:
        raise ImportError(f"Could not load spec for {mod_name} from {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


# ── M1 Models & Components ───────────────────────────────────────────────────
def get_m1_envelope_model() -> Any:
    path = os.path.join(WORKSPACE_ROOT, "M1", "modules", "m1-ingestion", "app", "envelope", "models.py")
    mod = load_mod("m1_envelope_models", path)
    return mod.RawEventEnvelope


# ── M2 Models & Components ───────────────────────────────────────────────────
def get_m2_raw_envelope_model() -> Any:
    path = os.path.join(WORKSPACE_ROOT, "M2", "abcd-main", "app", "models", "envelope.py")
    mod = load_mod("m2_envelope_models", path)
    return mod.RawEventEnvelope


def get_m2_parsed_event_model() -> Any:
    path = os.path.join(WORKSPACE_ROOT, "M2", "abcd-main", "app", "models", "parsed_event.py")
    mod = load_mod("m2_parsed_event_models", path)
    return mod.ParsedEvent


# ── M3 Models & Components ───────────────────────────────────────────────────
def get_m3_parsed_event_model() -> Any:
    path = os.path.join(WORKSPACE_ROOT, "M3", "app", "models", "parsed_event.py")
    mod = load_mod("m3_parsed_event_models", path)
    return mod.ParsedEvent


def get_m3_normalization_result_model() -> Any:
    path = os.path.join(WORKSPACE_ROOT, "M3", "app", "models", "normalization.py")
    mod = load_mod("m3_normalization_models", path)
    return mod.NormalizationResult


# ── M4 Models & Components ───────────────────────────────────────────────────
def get_m4_canonical_event_model() -> Any:
    m4_root = os.path.join(WORKSPACE_ROOT, "M4", "app")
    bind_package("app", m4_root)
    bind_package("app.models", os.path.join(m4_root, "models"))
    bind_package("app.contracts", os.path.join(m4_root, "contracts"))
    bind_package("app.errors", os.path.join(m4_root, "errors"))

    load_mod("app.errors.exceptions", os.path.join(m4_root, "errors", "exceptions.py"))
    load_mod("app.models.common", os.path.join(m4_root, "models", "common.py"))
    load_mod("app.contracts.integrity_contract", os.path.join(m4_root, "contracts", "integrity_contract.py"))
    load_mod("app.contracts.canonical_event", os.path.join(m4_root, "contracts", "canonical_event.py"))
    
    return sys.modules["app.contracts.canonical_event"].CanonicalEvent


def get_m4_enrichment_request_model() -> Any:
    m4_root = os.path.join(WORKSPACE_ROOT, "M4", "app")
    bind_package("app", m4_root)
    bind_package("app.models", os.path.join(m4_root, "models"))
    bind_package("app.contracts", os.path.join(m4_root, "contracts"))
    bind_package("app.errors", os.path.join(m4_root, "errors"))

    load_mod("app.errors.exceptions", os.path.join(m4_root, "errors", "exceptions.py"))
    load_mod("app.models.common", os.path.join(m4_root, "models", "common.py"))
    load_mod("app.contracts.integrity_contract", os.path.join(m4_root, "contracts", "integrity_contract.py"))
    load_mod("app.contracts.canonical_event", os.path.join(m4_root, "contracts", "canonical_event.py"))
    load_mod("app.contracts.provenance_contract", os.path.join(m4_root, "contracts", "provenance_contract.py"))
    load_mod("app.models.diagnostics", os.path.join(m4_root, "models", "diagnostics.py"))
    load_mod("app.models.tenant", os.path.join(m4_root, "models", "tenant.py"))
    mod_enrich = load_mod("app.contracts.enrichment_contract", os.path.join(m4_root, "contracts", "enrichment_contract.py"))
    
    return mod_enrich.EnrichmentRequest, mod_enrich.EnrichmentResult


# ── M5 Models & Components ───────────────────────────────────────────────────
def get_m5_router_components() -> Any:
    m5_root = os.path.join(WORKSPACE_ROOT, "M5", "app")
    bind_package("app", m5_root)
    bind_package("app.router", os.path.join(m5_root, "router"))

    load_mod("app.router.rules", os.path.join(m5_root, "router", "rules.py"))
    load_mod("app.router.evaluator", os.path.join(m5_root, "router", "evaluator.py"))
    router_mod = load_mod("app.router.router", os.path.join(m5_root, "router", "router.py"))
    rules_mod = sys.modules["app.router.rules"]

    return router_mod.SmartRouter, rules_mod.PolicyRule, rules_mod.RoutingDecision
