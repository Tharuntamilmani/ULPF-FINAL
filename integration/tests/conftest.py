"""
Pytest configuration for ULPF Integration Test Suite.
Configures sys.path so tests can import from M1-M6 and the integration package without modifying frozen modules.
"""

import sys
import os

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Ordered paths for module namespaces
MODULE_PATHS = [
    WORKSPACE_ROOT,
    os.path.join(WORKSPACE_ROOT, "M1", "modules", "m1-ingestion"),
    os.path.join(WORKSPACE_ROOT, "M2", "abcd-main"),
    os.path.join(WORKSPACE_ROOT, "M3"),
    os.path.join(WORKSPACE_ROOT, "M4"),
    os.path.join(WORKSPACE_ROOT, "M5"),
    os.path.join(WORKSPACE_ROOT, "M6", "M6-SIH-main"),
    os.path.join(WORKSPACE_ROOT, "M6", "M6-SIH-main", "backend"),
]

for p in MODULE_PATHS:
    if p not in sys.path and os.path.exists(p):
        sys.path.insert(0, p)
