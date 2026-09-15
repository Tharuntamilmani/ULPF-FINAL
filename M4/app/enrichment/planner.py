"""Enrichment planning and candidate selection for ULPF M4."""

from app.config.enrichment_config import EnrichmentConfiguration
from app.contracts.canonical_event import CanonicalEvent
from app.enrichment.precedence import sort_providers_deterministically
from app.enrichment.rules import RuleEvaluator
from app.providers.base import EnrichmentContext, EnrichmentProvider
from app.providers.registry import ProviderRegistry


class EnrichmentPlanner:
    """Plans and schedules provider execution for a canonical event."""

    def __init__(self, registry: ProviderRegistry) -> None:
        self.registry = registry

    def plan_execution(
        self,
        event: CanonicalEvent,
        config: EnrichmentConfiguration,
        context: EnrichmentContext,
    ) -> list[EnrichmentProvider]:
        """Determine applicable providers based on enabled set, rules, and event shape."""
        tenant_id = context.tenant_context.tenant_id

        # Check tenant scope on configuration
        if "*" not in config.tenant_scopes and tenant_id not in config.tenant_scopes:
            return []

        # Find enabled provider instances
        enabled_instances: list[EnrichmentProvider] = []
        for pid in config.enabled_providers:
            provider = self.registry.get(pid)
            if provider is not None:
                enabled_instances.append(provider)

        # Check if rules are defined
        targeted_provider_ids: set[str] = set()
        active_rules = [r for r in config.rules if r.enabled]

        if active_rules:
            for rule in active_rules:
                if RuleEvaluator.evaluate_rule(event, rule, tenant_id):
                    targeted_provider_ids.update(rule.providers)

        # Select candidates
        candidates: list[EnrichmentProvider] = []
        for provider in enabled_instances:
            # If rules exist and targeted this provider, or if no rules explicitly target
            if active_rules and provider.provider_id not in targeted_provider_ids:
                continue

            if provider.can_enrich(event, context):
                candidates.append(provider)

        # Sort deterministically
        return sort_providers_deterministically(candidates, config)
