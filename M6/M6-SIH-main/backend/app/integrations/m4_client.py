"""M4 Enrichment service client."""

from __future__ import annotations

from backend.app.core.config import get_settings
from backend.app.integrations.http_module_client import HttpModuleClient
from backend.app.integrations.mock_module_client import MockModuleClient
from backend.app.integrations.module_client import ModuleClient


def get_m4_client() -> ModuleClient:
    settings = get_settings()
    if settings.use_mock_adapters:
        return MockModuleClient("m4-enrichment")
    return HttpModuleClient("m4-enrichment", settings.m4_base_url or None)
