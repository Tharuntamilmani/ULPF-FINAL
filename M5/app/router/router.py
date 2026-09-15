"""
Smart Router implementing deterministic policy evaluation and multi-destination decision audit logging.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from app.router.evaluator import evaluate_condition, extract_field_value
from app.router.rules import PolicyRule, RoutingDecision


class SmartRouter:
    """
    Smart Router evaluates UES v1 events against loaded delivery policies
    and produces deterministic routing decisions without modifying the UES event.
    """

    def __init__(self, rules: Optional[List[PolicyRule]] = None):
        self.rules: List[PolicyRule] = []
        if rules:
            self.set_rules(rules)

    def set_rules(self, rules: List[PolicyRule]) -> None:
        """
        Set and sort policy rules deterministically by priority (highest priority first), then rule ID.
        """
        self.rules = sorted(rules, key=lambda r: (-r.priority, r.id))

    def extract_event_id(self, event: Dict[str, Any]) -> str:
        """
        Extract the canonical event ID from UES event.
        Primary key is 'event.id' or top-level 'event_id' or 'id'.
        """
        event_id = extract_field_value(event, "event.id")
        if not event_id:
            event_id = event.get("event_id") or event.get("id") or "unknown_event_id"
        return str(event_id)

    def extract_tenant_id(self, event: Dict[str, Any]) -> Optional[str]:
        """
        Extract tenant identity from UES event context.
        """
        tenant_id = extract_field_value(event, "tenant.id")
        if not tenant_id:
            tenant_id = event.get("tenant_id") or extract_field_value(event, "tenant_id")
        return str(tenant_id) if tenant_id else None

    def route(self, event: Dict[str, Any]) -> Tuple[List[str], RoutingDecision]:
        """
        Evaluate all matching policies for the given event and aggregate target destinations.
        Returns a tuple of (unique_destinations, decision_object).
        """
        event_id = self.extract_event_id(event)
        tenant_id = self.extract_tenant_id(event)

        matched_policies: List[str] = []
        target_destinations: List[str] = []

        for rule in self.rules:
            # Check if rule is enabled
            if not getattr(rule, "enabled", True):
                continue

            # Check tenant alignment if specified on the rule
            if rule.tenant_id and rule.tenant_id != tenant_id:
                continue

            # Evaluate policy condition
            is_match = False
            if rule.when is None:
                is_match = True
            else:
                is_match = evaluate_condition(event, rule.when)

            if is_match:
                matched_policies.append(rule.id)
                for dest in rule.destinations:
                    if dest not in target_destinations:
                        target_destinations.append(dest)

        decision = RoutingDecision(
            event_id=event_id,
            matched_policies=matched_policies,
            destinations=target_destinations,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            tenant_id=tenant_id
        )

        return target_destinations, decision
