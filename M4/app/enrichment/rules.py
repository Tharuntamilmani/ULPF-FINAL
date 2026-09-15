"""Declarative Enrichment Rule Evaluation Engine for ULPF M4."""

import re
from typing import Any

from app.config.enrichment_config import ConditionRule, EnrichmentRuleConfig
from app.contracts.canonical_event import CanonicalEvent


def _get_nested_field(obj: Any, path: str) -> Any:
    """Safely traverse a nested dot-separated field path on a Pydantic model or dict."""
    parts = path.split(".")
    curr = obj
    for part in parts:
        if curr is None:
            return None
        if isinstance(curr, dict):
            curr = curr.get(part)
        elif hasattr(curr, part):
            curr = getattr(curr, part)
        else:
            return None
    return curr


class RuleEvaluator:
    """Evaluates declarative conditions and rules against canonical events."""

    @staticmethod
    def evaluate_condition(event: CanonicalEvent, cond: ConditionRule) -> bool:
        """Evaluate a single ConditionRule against the event."""
        val = _get_nested_field(event, cond.field)

        if cond.operator == "exists":
            return val is not None and val != ""

        if cond.operator == "not_exists":
            return val is None or val == ""

        if cond.operator == "equals":
            return bool(val == cond.value)

        if cond.operator == "in_list":
            if isinstance(cond.value, list | tuple | set):
                return bool(val in cond.value)
            return False

        if cond.operator == "regex_match":
            if val is None or cond.value is None:
                return False
            try:
                pattern = re.compile(str(cond.value))
                return bool(pattern.search(str(val)))
            except re.error:
                return False

        return False

    @classmethod
    def evaluate_rule(
        cls, event: CanonicalEvent, rule: EnrichmentRuleConfig, tenant_id: str
    ) -> bool:
        """Evaluate whether a rule triggers for the event and tenant."""
        if not rule.enabled:
            return False

        # Check tenant scope
        if "*" not in rule.tenant_scope and tenant_id not in rule.tenant_scope:
            return False

        # All conditions must match (AND)
        return all(cls.evaluate_condition(event, c) for c in rule.conditions)
