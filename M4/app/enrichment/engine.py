"""Core Enrichment Engine orchestrating planning, execution, merge, provenance, and integrity."""

import time

from app.cache.base import EnrichmentCache
from app.config.lifecycle import ConfigurationManager
from app.contracts.canonical_event import CanonicalEvent
from app.contracts.enrichment_contract import EnrichmentRequest, EnrichmentResult
from app.errors.exceptions import (
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.integrity.verifier import calculate_integrity
from app.models.common import CacheStatus, EnrichmentStatus
from app.models.diagnostics import EnrichmentDiagnostic, ProviderDiagnostic
from app.models.tenant import TenantContext
from app.observability.logging import setup_logging
from app.observability.metrics import (
    CACHE_OPERATIONS,
    EVENTS_ENRICHED,
    EVENTS_RECEIVED,
    PROVIDER_CALLS,
    PROVIDER_LATENCY,
)
from app.provenance.tracker import ProvenanceTracker
from app.providers.base import EnrichmentContext, EnrichmentProvider, ProviderOutput
from app.providers.registry import ProviderRegistry
from app.security.tenant_guard import TenantGuard
from app.validation.input_validator import InputValidator
from app.validation.result_validator import ResultValidator

from .merger import AdditiveMerger
from .planner import EnrichmentPlanner

logger = setup_logging()


class EnrichmentEngine:
    """Production-grade orchestration engine for ULPF Module M4."""

    def __init__(
        self,
        registry: ProviderRegistry,
        config_manager: ConfigurationManager,
        cache: EnrichmentCache | None = None,
    ) -> None:
        self.registry = registry
        self.config_manager = config_manager
        self.cache = cache
        self.planner = EnrichmentPlanner(registry)

    def _get_lookup_key(self, event: CanonicalEvent, provider: EnrichmentProvider) -> str:
        """Derive standard lookup key based on provider target namespace and event fields."""
        if provider.target_namespace == "asset":
            return (
                (event.source and event.source.ip)
                or (event.host and event.host.hostname)
                or (event.host and event.host.name)
                or "unknown"
            )
        if provider.target_namespace == "geo":
            return (
                (event.source and event.source.ip)
                or (event.destination and event.destination.ip)
                or "unknown"
            )
        if provider.target_namespace == "threat_intel":
            return (
                (event.destination and event.destination.domain)
                or (event.destination and event.destination.ip)
                or (event.source and event.source.ip)
                or "unknown"
            )
        return event.source.ip or event.event.id

    def process(self, request: EnrichmentRequest) -> EnrichmentResult:
        """Execute the full enrichment pipeline on an incoming enrichment request."""
        start_time = time.perf_counter()
        EVENTS_RECEIVED.inc()

        # Step 1: Input Validation
        validated_event = InputValidator.validate_event(request.event)
        # Retain deep copy for preservation verification
        original_copy = validated_event.model_copy(deep=True)

        # Step 2: Resolve Configuration
        if request.configuration_version:
            config = self.config_manager.get_version(request.configuration_version)
            if not config:
                config = self.config_manager.get_active()
        else:
            config = self.config_manager.get_active()

        # Step 3: Resolve & Validate Tenant Context
        if request.tenant_context is not None:
            tenant_context = request.tenant_context
        else:
            tenant_context = TenantContext(
                tenant_id=validated_event.tenant.tenant_id,
                scope=validated_event.tenant.scope,
                configuration_version=config.version,
            )

        TenantGuard.validate_event_tenant(validated_event, tenant_context)

        # Step 4: Plan Enrichment Providers
        enrichment_context = EnrichmentContext(
            tenant_context=tenant_context,
            configuration_version=config.version,
            options=request.options,
        )
        planned_providers = self.planner.plan_execution(validated_event, config, enrichment_context)

        # Step 5: Execute Providers & Track Diagnostics
        tracker = ProvenanceTracker(configuration_version=config.version)
        provider_diagnostics: list[ProviderDiagnostic] = []
        bypass_cache = request.options.get("bypass_cache", False)

        providers_succeeded = 0
        providers_failed = 0
        providers_timed_out = 0
        providers_not_found = 0

        working_event = validated_event

        for provider in planned_providers:
            lookup_key = self._get_lookup_key(working_event, provider)
            is_global = not provider.is_tenant_sensitive
            p_start = time.perf_counter()

            # Cache check
            cached_entry = None
            if self.cache is not None and config.cache_enabled and not bypass_cache:
                cached_entry = self.cache.get(
                    tenant_id=tenant_context.tenant_id,
                    provider_id=provider.provider_id,
                    lookup_type=provider.target_namespace,
                    lookup_key=lookup_key,
                    is_global=is_global,
                )

            if cached_entry is not None:
                CACHE_OPERATIONS.labels(provider=provider.provider_id, result="hit").inc()
                PROVIDER_CALLS.labels(
                    provider=provider.provider_id, status=EnrichmentStatus.SUCCESS.value
                ).inc()

                # Add cached data
                cached_output = ProviderOutput(
                    status=EnrichmentStatus.SUCCESS,
                    data=cached_entry.data,
                    confidence=cached_entry.provenance.confidence,
                    source_reference=cached_entry.provenance.source_reference,
                )
                working_event = AdditiveMerger.merge_output(
                    working_event, provider.target_namespace, cached_output
                )
                tracker.record_operation(
                    provider_id=provider.provider_id,
                    provider_version=provider.provider_version,
                    enrichment_type=provider.target_namespace,
                    output=cached_output,
                    cache_status=CacheStatus.HIT,
                )
                p_duration = (time.perf_counter() - p_start) * 1000.0
                provider_diagnostics.append(
                    ProviderDiagnostic(
                        provider_id=provider.provider_id,
                        provider_version=provider.provider_version,
                        status=EnrichmentStatus.SUCCESS,
                        duration_ms=round(p_duration, 2),
                        cached=True,
                    )
                )
                providers_succeeded += 1
                continue

            if self.cache is not None and config.cache_enabled and not bypass_cache:
                CACHE_OPERATIONS.labels(provider=provider.provider_id, result="miss").inc()

            # Execute provider with deadline & failure isolation
            output: ProviderOutput
            diag_status: EnrichmentStatus = EnrichmentStatus.SUCCESS
            error_msg: str | None = None
            error_type: str | None = None

            try:
                output = provider.enrich(working_event, enrichment_context)
                diag_status = output.status

                if output.status == EnrichmentStatus.SUCCESS:
                    ResultValidator.validate_output(provider.provider_id, output)
                    working_event = AdditiveMerger.merge_output(
                        working_event, provider.target_namespace, output
                    )
                    providers_succeeded += 1

                    # Populate cache
                    if self.cache is not None and config.cache_enabled and not bypass_cache:
                        ttl = config.provider_timeouts.get(
                            provider.provider_id, config.cache_ttl_seconds
                        )
                        prov_record = tracker.record_operation(
                            provider_id=provider.provider_id,
                            provider_version=provider.provider_version,
                            enrichment_type=provider.target_namespace,
                            output=output,
                            cache_status=CacheStatus.MISS,
                        )
                        self.cache.set(
                            tenant_id=tenant_context.tenant_id,
                            provider_id=provider.provider_id,
                            lookup_type=provider.target_namespace,
                            lookup_key=lookup_key,
                            data=output.data,
                            provenance=prov_record,
                            ttl_seconds=int(ttl),
                            is_global=is_global,
                        )
                    else:
                        tracker.record_operation(
                            provider_id=provider.provider_id,
                            provider_version=provider.provider_version,
                            enrichment_type=provider.target_namespace,
                            output=output,
                            cache_status=CacheStatus.BYPASS,
                        )

                elif output.status == EnrichmentStatus.NOT_FOUND:
                    providers_not_found += 1
                    error_msg = output.error_message
                    tracker.record_operation(
                        provider_id=provider.provider_id,
                        provider_version=provider.provider_version,
                        enrichment_type=provider.target_namespace,
                        output=output,
                        cache_status=CacheStatus.MISS,
                    )
                else:
                    providers_failed += 1
                    error_msg = output.error_message
                    error_type = output.error_type or "ProviderExecutionFailure"
                    tracker.record_operation(
                        provider_id=provider.provider_id,
                        provider_version=provider.provider_version,
                        enrichment_type=provider.target_namespace,
                        output=output,
                        cache_status=CacheStatus.MISS,
                    )

            except ProviderTimeoutError as e:
                diag_status = EnrichmentStatus.TIMEOUT
                providers_timed_out += 1
                error_msg = str(e)
                error_type = "ProviderTimeoutError"
                output = ProviderOutput(
                    status=EnrichmentStatus.TIMEOUT,
                    error_message=error_msg,
                    error_type=error_type,
                )
                tracker.record_operation(
                    provider_id=provider.provider_id,
                    provider_version=provider.provider_version,
                    enrichment_type=provider.target_namespace,
                    output=output,
                    cache_status=CacheStatus.MISS,
                )

            except (ProviderResponseError, ProviderUnavailableError, Exception) as e:
                diag_status = EnrichmentStatus.FAILED
                providers_failed += 1
                error_msg = str(e)
                error_type = type(e).__name__
                output = ProviderOutput(
                    status=EnrichmentStatus.FAILED,
                    error_message=error_msg,
                    error_type=error_type,
                )
                tracker.record_operation(
                    provider_id=provider.provider_id,
                    provider_version=provider.provider_version,
                    enrichment_type=provider.target_namespace,
                    output=output,
                    cache_status=CacheStatus.MISS,
                )

            p_duration = (time.perf_counter() - p_start) * 1000.0
            PROVIDER_CALLS.labels(provider=provider.provider_id, status=diag_status.value).inc()
            PROVIDER_LATENCY.labels(provider=provider.provider_id).observe(p_duration / 1000.0)

            provider_diagnostics.append(
                ProviderDiagnostic(
                    provider_id=provider.provider_id,
                    provider_version=provider.provider_version,
                    status=diag_status,
                    duration_ms=round(p_duration, 2),
                    error_message=error_msg,
                    error_type=error_type,
                    cached=False,
                )
            )

        # Step 6: Verify Preservation Invariants
        AdditiveMerger.verify_invariants(original_copy, working_event)

        # Step 7: Attach Provenance
        working_event = tracker.attach_to_event(working_event)

        # Step 8: Calculate Cryptographic Integrity (Enriched Phase)
        integrity_meta = calculate_integrity(working_event, phase="enriched")
        working_event.integrity = integrity_meta

        # Step 9: Determine Overall Enrichment Status
        total_attempted = len(planned_providers)
        overall_status: EnrichmentStatus

        if total_attempted == 0:
            overall_status = EnrichmentStatus.SKIPPED
        elif providers_failed > 0 or providers_timed_out > 0:
            if providers_succeeded > 0:
                overall_status = EnrichmentStatus.PARTIAL
            else:
                overall_status = (
                    EnrichmentStatus.TIMEOUT
                    if providers_timed_out == total_attempted
                    else EnrichmentStatus.FAILED
                )
        elif providers_succeeded > 0:
            overall_status = EnrichmentStatus.SUCCESS
        elif providers_not_found > 0:
            overall_status = EnrichmentStatus.NOT_FOUND
        else:
            overall_status = EnrichmentStatus.SKIPPED

        EVENTS_ENRICHED.labels(status=overall_status.value).inc()
        total_duration_ms = (time.perf_counter() - start_time) * 1000.0

        diagnostics = EnrichmentDiagnostic(
            total_duration_ms=round(total_duration_ms, 2),
            providers_attempted=total_attempted,
            providers_succeeded=providers_succeeded,
            providers_failed=providers_failed,
            providers_timed_out=providers_timed_out,
            providers_not_found=providers_not_found,
            provider_diagnostics=provider_diagnostics,
        )

        return EnrichmentResult(
            event=working_event,
            status=overall_status,
            provenance=tracker.get_records(),
            diagnostics=diagnostics,
            integrity=integrity_meta,
        )
