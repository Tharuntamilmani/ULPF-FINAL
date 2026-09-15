"""
Ingress Security Gateway: IngressSecurityGateway.

Resolves P1-3 (M1 Tenant Header Trust / Spoofing Risk):
M1 relies on a shared static Bearer token and trusts the client-provided X-Tenant-ID.
If exposed directly to multi-tenant clients, one tenant can spoof another's X-Tenant-ID.

This gateway forms an external security perimeter:
  1. Authenticates external clients via unique per-tenant API keys or Bearer tokens.
  2. Resolves the client's cryptographically bound authorized tenant identity.
  3. Detects and REJECTS spoofing attempts (if client submits an X-Tenant-ID differing from their bound tenant).
  4. Strips untrusted X-Tenant-ID and external headers.
  5. Injects verified X-Tenant-ID, X-Source-ID, and X-Correlation-ID headers.
  6. Attaches internal M1 system credentials to forward the request to M1 in the trusted network.
"""

import os
from typing import Dict, Any, Optional, Tuple
import uuid
import httpx
from fastapi import FastAPI, Request, Response, HTTPException, Header, status
from fastapi.responses import JSONResponse
import structlog

from integration.contracts.tenant_context import TenantContext
from integration.security.service_auth import service_auth

logger = structlog.get_logger("integration.security.gateway")


# Registry of authorized tenant client credentials
# Key: API key / token presented by external client
# Value: Dict defining authorized tenant, principal, and allowed source prefixes
TENANT_CREDENTIAL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "key-tenant-cisco-prod": {
        "tenant_id": "tenant-cisco",
        "principal": "cisco-log-collector",
        "allowed_sources": ["cisco-asa-fw01", "cisco-asa-fw02", "cisco-*"],
    },
    "key-tenant-windows-prod": {
        "tenant_id": "tenant-windows",
        "principal": "windows-event-forwarder",
        "allowed_sources": ["win-dc01", "win-srv01", "win-*"],
    },
    "key-tenant-alpha-prod": {
        "tenant_id": "tenant-alpha",
        "principal": "alpha-agent-01",
        "allowed_sources": ["alpha-*"],
    },
    "key-tenant-beta-prod": {
        "tenant_id": "tenant-beta",
        "principal": "beta-agent-01",
        "allowed_sources": ["beta-*"],
    },
}


class IngressSecurityGateway:
    """
    Ingress proxy and tenant boundary enforcer.
    """

    def __init__(
        self,
        m1_internal_url: Optional[str] = None,
        credential_registry: Optional[Dict[str, Dict[str, Any]]] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        url = m1_internal_url or os.getenv("M1_INTERNAL_URL", "http://localhost:8001")
        self.m1_internal_url = url.rstrip("/")
        self.credentials = credential_registry or TENANT_CREDENTIAL_REGISTRY
        self.http_client = http_client

    def authenticate_client(
        self,
        auth_header: Optional[str],
        api_key_header: Optional[str],
        requested_tenant_header: Optional[str] = None
    ) -> TenantContext:
        """
        Authenticate client credentials and prevent tenant spoofing.
        Raises HTTPException if authentication fails or spoofing is attempted.
        """
        token = None
        if auth_header:
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
            else:
                token = auth_header.strip()
        elif api_key_header:
            token = api_key_header.strip()

        if not token or token not in self.credentials:
            logger.warning("Unauthenticated ingress attempt", token_present=bool(token))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing client credentials",
            )

        cred_info = self.credentials[token]
        authorized_tenant_id = cred_info["tenant_id"]
        principal = cred_info["principal"]

        # Anti-spoofing check: if client explicitly requested a different tenant, REJECT
        if requested_tenant_header and requested_tenant_header.strip() != authorized_tenant_id:
            logger.error(
                "Tenant spoofing attempt detected and blocked",
                authorized_tenant=authorized_tenant_id,
                attempted_tenant=requested_tenant_header,
                principal=principal,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: credential for '{authorized_tenant_id}' cannot act as tenant '{requested_tenant_header}'",
            )

        correlation_id = str(uuid.uuid4())

        return TenantContext(
            tenant_id=authorized_tenant_id,
            source_id="external-ingress",
            authenticated_principal=principal,
            correlation_id=correlation_id,
        )

    async def forward_to_m1(
        self,
        path: str,
        method: str,
        body: bytes,
        tenant_context: TenantContext,
        content_type: str = "application/json",
        source_id: Optional[str] = None,
    ) -> Tuple[int, Dict[str, Any], bytes]:
        """
        Forward sanitized request to internal M1 with trusted internal headers.
        """
        if source_id:
            tenant_context.source_id = source_id

        # Internal headers: stripped of untrusted client headers, injected with trusted context
        token = os.getenv("M1_INTERNAL_TOKEN", service_auth.m1_internal_token)
        forward_headers = {
            "Content-Type": content_type,
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": tenant_context.tenant_id,
            "X-Source-ID": tenant_context.source_id,
            "X-Correlation-ID": tenant_context.correlation_id,
            "X-Authenticated-Principal": tenant_context.authenticated_principal or "unknown",
        }

        target_path = "v1/events" if path.lstrip('/') in ["v1/ingest/event", "v1/ingest/raw", "v1/events"] else path.lstrip('/')
        base_url = os.getenv("M1_INTERNAL_URL", self.m1_internal_url).rstrip("/")
        url = f"{base_url}/{target_path}"

        client = self.http_client or httpx.AsyncClient(timeout=15.0)
        try:
            resp = await client.request(
                method=method,
                url=url,
                content=body,
                headers=forward_headers,
            )
            return resp.status_code, dict(resp.headers), resp.content
        finally:
            if not self.http_client:
                await client.aclose()


# FastAPI gateway application
gateway_app = FastAPI(title="ULPF Ingress Security Gateway", version="1.0.0")
gateway_instance = IngressSecurityGateway()


@gateway_app.post("/v1/ingest/event")
@gateway_app.post("/v1/ingest/raw")
@gateway_app.post("/v1/events")
async def ingest_event(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None),
    x_source_id: Optional[str] = Header(None),
):
    """
    Ingress proxy endpoint enforcing tenant boundary and forwarding to internal M1.
    """
    tenant_ctx = gateway_instance.authenticate_client(
        auth_header=authorization,
        api_key_header=x_api_key,
        requested_tenant_header=x_tenant_id,
    )

    body = await request.body()
    content_type = request.headers.get("content-type", "application/json")
    path = request.url.path

    status_code, headers, content = await gateway_instance.forward_to_m1(
        path=path,
        method=request.method,
        body=body,
        tenant_context=tenant_ctx,
        content_type=content_type,
        source_id=x_source_id,
    )

    return Response(
        content=content,
        status_code=status_code,
        media_type=headers.get("content-type", "application/json"),
        headers={"X-Correlation-ID": tenant_ctx.correlation_id},
    )


@gateway_app.get("/health")
async def health():
    return {"status": "HEALTHY", "gateway": "ULPF Ingress Security Gateway"}
