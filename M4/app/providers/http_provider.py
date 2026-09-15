"""Hardened HTTP Enrichment Provider with SSRF Protection and Resource Bounds."""

import httpx

from app.contracts.canonical_event import CanonicalEvent
from app.errors.exceptions import (
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    SSRFViolationError,
)
from app.models.common import EnrichmentStatus
from app.providers.base import EnrichmentContext, EnrichmentProvider, ProviderOutput
from app.security.ssrf_guard import SSRFGuard

MAX_RESPONSE_BYTES = 1024 * 1024  # 1 MB response limit


class HardenedHttpProvider(EnrichmentProvider):
    """Enriches events via HTTP API endpoints with SSRF guardrails and resource bounds."""

    def __init__(
        self,
        provider_id: str,
        base_url: str,
        provider_version: str = "1.0.0",
        target_namespace: str = "external_api",
        priority: int = 80,
        timeout_seconds: float = 3.0,
        allowed_domains: set[str] | None = None,
        allow_http: bool = False,
        is_tenant_sensitive: bool = True,
        client: httpx.Client | None = None,
    ) -> None:
        super().__init__(
            provider_id=provider_id,
            provider_version=provider_version,
            target_namespace=target_namespace,
            priority=priority,
            timeout_seconds=timeout_seconds,
            is_tenant_sensitive=is_tenant_sensitive,
        )
        self.base_url = base_url
        self.ssrf_guard = SSRFGuard(allowed_domains=allowed_domains, allow_http=allow_http)
        self._custom_client = client

    def can_enrich(self, event: CanonicalEvent, context: EnrichmentContext) -> bool:
        return bool(event.source and event.source.ip)

    def enrich(self, event: CanonicalEvent, context: EnrichmentContext) -> ProviderOutput:
        # Validate base_url against SSRF rules before connection
        try:
            validated_url = self.ssrf_guard.validate_url(self.base_url)
        except SSRFViolationError as e:
            return ProviderOutput(
                status=EnrichmentStatus.FAILED,
                error_message=f"SSRF validation rejected URL: {e}",
                error_type="SSRFViolationError",
            )

        endpoint_url = f"{validated_url.rstrip('/')}/lookup"
        # Re-validate full URL
        try:
            self.ssrf_guard.validate_url(endpoint_url)
        except SSRFViolationError as e:
            return ProviderOutput(
                status=EnrichmentStatus.FAILED,
                error_message=f"SSRF validation rejected endpoint URL: {e}",
                error_type="SSRFViolationError",
            )

        lookup_param = event.source.ip or "unknown"
        headers = {
            "Accept": "application/json",
            "User-Agent": f"ULPF-M4-Provider/{self.provider_version}",
            "X-Tenant-ID": context.tenant_context.tenant_id,
        }

        try:
            # Use custom client if provided, else create scoped client
            if self._custom_client:
                response = self._custom_client.get(
                    endpoint_url,
                    params={"ip": lookup_param},
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.get(
                        endpoint_url,
                        params={"ip": lookup_param},
                        headers=headers,
                    )

            if len(response.content) > MAX_RESPONSE_BYTES:
                raise ProviderResponseError(
                    f"Provider response size {len(response.content)} exceeded maximum allowed limit {MAX_RESPONSE_BYTES}"
                )

            if response.status_code == 404:
                return ProviderOutput(
                    status=EnrichmentStatus.NOT_FOUND,
                    error_message=f"Entity not found in remote provider {self.provider_id}",
                )

            if response.status_code != 200:
                return ProviderOutput(
                    status=EnrichmentStatus.FAILED,
                    error_message=f"Remote HTTP provider returned status code {response.status_code}",
                    error_type="HttpError",
                )

            json_data = response.json()
            if not isinstance(json_data, dict):
                raise ProviderResponseError("Remote HTTP response body is not a JSON object")

            return ProviderOutput(
                status=EnrichmentStatus.SUCCESS,
                data=json_data.get("data", json_data),
                confidence=float(json_data.get("confidence", 0.85)),
                source_reference=f"http://{self.provider_id}",
            )

        except httpx.TimeoutException as e:
            raise ProviderTimeoutError(
                f"HTTP provider '{self.provider_id}' timed out after {self.timeout_seconds}s: {e}"
            ) from e
        except (httpx.RequestError, ConnectionError) as e:
            raise ProviderUnavailableError(
                f"Failed connecting to provider '{self.provider_id}': {e}"
            ) from e
        except ValueError as e:
            raise ProviderResponseError(
                f"Invalid JSON returned by provider '{self.provider_id}': {e}"
            ) from e
