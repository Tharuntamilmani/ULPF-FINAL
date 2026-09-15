"""M4 enrichment engine export."""

from app.enrichment.engine import EnrichmentEngine
from app.enrichment.merger import AdditiveMerger
from app.enrichment.planner import EnrichmentPlanner
from app.enrichment.precedence import (
    get_provider_sort_key,
    sort_providers_deterministically,
)
from app.enrichment.rules import RuleEvaluator

__all__ = [
    "EnrichmentEngine",
    "AdditiveMerger",
    "EnrichmentPlanner",
    "RuleEvaluator",
    "get_provider_sort_key",
    "sort_providers_deterministically",
]
