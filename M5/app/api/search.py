"""
FastAPI search and policy management endpoints: POST /v1/events/search, GET /v1/routes, GET /v1/policies.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
import app.api.events as events_api
from app.api.auth import get_current_tenant_context, TenantContext
from app.policy.engine import PolicyEngine
from app.router.evaluator import extract_field_value

router = APIRouter(prefix="/v1", tags=["Search & Policy Management"])

policy_engine_ref: Optional[PolicyEngine] = None


def set_policy_engine(engine: PolicyEngine) -> None:
    global policy_engine_ref
    policy_engine_ref = engine


class EventSearchQuery(BaseModel):
    event_type: Optional[str] = None
    min_severity: Optional[int] = None
    max_severity: Optional[int] = None
    is_security_event: Optional[bool] = None
    query_string: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=500)


@router.post("/events/search")
async def search_events(
    body: EventSearchQuery,
    x_tenant_id: Optional[str] = Header(None),
    context: Optional[TenantContext] = Depends(get_current_tenant_context)
):
    """
    POST multi-criteria event search with strict tenant isolation.
    """
    connector = events_api.opensearch_connector_ref
    if not connector:
        raise HTTPException(status_code=503, detail="Storage connector uninitialized")

    req_tenant, is_admin = events_api.resolve_effective_tenant(x_tenant_id, context)
    matches: List[Dict[str, Any]] = []

    for doc_id, doc in connector.mock_storage.items():

        event = doc.get("canonical_ues", {})
        event_tenant = str(extract_field_value(event, "tenant.id") or event.get("tenant_id") or "default_tenant")

        # Tenant isolation
        if not is_admin and req_tenant != event_tenant:
            continue

        if body.event_type:
            if extract_field_value(event, "event.type") != body.event_type:
                continue

        if body.min_severity is not None:
            sev = extract_field_value(event, "event.severity.value")
            if sev is None or float(sev) < float(body.min_severity):
                continue

        if body.max_severity is not None:
            sev = extract_field_value(event, "event.severity.value")
            if sev is None or float(sev) > float(body.max_severity):
                continue

        if body.is_security_event is not None:
            sec = extract_field_value(event, "security.is_security_event")
            if bool(sec) != body.is_security_event:
                continue

        matches.append(event)
        if len(matches) >= body.limit:
            break

    return {
        "count": len(matches),
        "tenant_id": req_tenant,
        "events": matches
    }


@router.get("/policies")
async def get_policies():
    """
    Get active delivery policy rules.
    """
    if not policy_engine_ref:
        raise HTTPException(status_code=503, detail="Policy engine uninitialized")

    policies = policy_engine_ref.list_policies()
    return {
        "count": len(policies),
        "policies": [p.model_dump() for p in policies]
    }


@router.get("/routes")
async def get_routes():
    """
    Get current smart router active destinations and routing summary.
    """
    if not policy_engine_ref:
        raise HTTPException(status_code=503, detail="Policy engine uninitialized")

    policies = policy_engine_ref.list_policies()
    destinations = set()
    for p in policies:
        destinations.update(p.destinations)

    return {
        "active_destinations": sorted(list(destinations)),
        "policy_count": len(policies)
    }
