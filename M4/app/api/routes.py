"""Core API routes for ULPF M4."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_config_manager, get_engine, get_registry
from app.api.security import AuthenticatedPrincipal, require_roles
from app.config.enrichment_config import EnrichmentConfiguration
from app.config.lifecycle import ConfigurationManager
from app.contracts.canonical_event import CanonicalEvent
from app.contracts.enrichment_contract import EnrichmentRequest, EnrichmentResult
from app.enrichment.engine import EnrichmentEngine
from app.errors.exceptions import InvalidEventError, TenantScopeError
from app.integrity.verifier import calculate_integrity, verify_integrity
from app.models.common import ApiRole
from app.observability.metrics import INTEGRITY_VERIFICATIONS
from app.providers.base import ProviderMetadata
from app.providers.registry import ProviderRegistry

router = APIRouter(prefix="/v1", tags=["Enrichment & Integrity"])


class VerifyRequest(BaseModel):
    """Payload to cryptographically verify an event's digest."""

    event: CanonicalEvent | dict[str, Any]
    expected_digest: str | None = Field(
        default=None,
        description="Expected SHA-256 digest; if omitted, event.integrity.digest is used",
    )
    phase: str = Field(default="enriched", description="Phase of event verified")


class VerifyResponse(BaseModel):
    """Result of cryptographic integrity verification."""

    valid: bool
    computed_digest: str
    phase: str
    verified_at: str


@router.post(
    "/enrich",
    response_model=EnrichmentResult,
    summary="Enrich a Canonical UES Event",
)
def enrich_event(
    request: EnrichmentRequest,
    engine: EnrichmentEngine = Depends(get_engine),
    principal: AuthenticatedPrincipal = Depends(
        require_roles(ApiRole.EVENT_PROCESSING, ApiRole.ADMIN)
    ),
) -> EnrichmentResult:
    """Enrich a canonical UES event with assets, GeoIP, threat intel, and cryptographic integrity."""
    # Enforce API key tenant scope if constrained
    if principal.allowed_tenant_scope != "*":
        target_tenant = (
            request.tenant_context.tenant_id
            if request.tenant_context
            else request.event.tenant.tenant_id
        )
        if target_tenant != principal.allowed_tenant_scope:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Principal tenant scope '{principal.allowed_tenant_scope}' does not allow processing for tenant '{target_tenant}'",
            )

    try:
        return engine.process(request)
    except (InvalidEventError, TenantScopeError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal enrichment engine error: {e}",
        ) from e


@router.post(
    "/verify",
    response_model=VerifyResponse,
    summary="Verify Event Cryptographic Integrity",
)
def verify_event_integrity(
    request: VerifyRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_roles(ApiRole.EVENT_PROCESSING, ApiRole.ANALYST_READ, ApiRole.ADMIN)
    ),
) -> VerifyResponse:
    """Verify that an event's content strictly matches its cryptographic SHA-256 digest."""
    try:
        computed = calculate_integrity(request.event, phase=request.phase)
        is_valid = verify_integrity(
            request.event,
            expected_digest=request.expected_digest,
            phase=request.phase,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed calculating integrity digest: {e}",
        ) from e

    result_label = "valid" if is_valid else "invalid"
    INTEGRITY_VERIFICATIONS.labels(result=result_label).inc()

    return VerifyResponse(
        valid=is_valid,
        computed_digest=computed.digest,
        phase=request.phase,
        verified_at=datetime.now(UTC).isoformat(),
    )


@router.get(
    "/providers",
    response_model=list[ProviderMetadata],
    summary="List Registered Providers",
)
def list_providers(
    registry: ProviderRegistry = Depends(get_registry),
    principal: AuthenticatedPrincipal = Depends(require_roles(ApiRole.ANALYST_READ, ApiRole.ADMIN)),
) -> list[ProviderMetadata]:
    """Retrieve metadata for all registered enrichment providers."""
    return registry.list_providers()


@router.get(
    "/configuration",
    response_model=EnrichmentConfiguration,
    summary="Get Active Configuration",
)
def get_active_configuration(
    config_mgr: ConfigurationManager = Depends(get_config_manager),
    principal: AuthenticatedPrincipal = Depends(require_roles(ApiRole.ANALYST_READ, ApiRole.ADMIN)),
) -> EnrichmentConfiguration:
    """Retrieve the currently active versioned enrichment configuration."""
    return config_mgr.get_active()
