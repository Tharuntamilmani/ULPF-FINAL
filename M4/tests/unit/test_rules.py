"""Unit tests for the declarative enrichment rule engine."""

from app.config.enrichment_config import ConditionRule, EnrichmentRuleConfig
from app.contracts.canonical_event import CanonicalEvent
from app.enrichment.rules import RuleEvaluator


def test_rule_condition_exists(sample_canonical_event: CanonicalEvent) -> None:
    """Test 'exists' operator."""
    cond = ConditionRule(field="source.ip", operator="exists")
    assert RuleEvaluator.evaluate_condition(sample_canonical_event, cond) is True

    cond_missing = ConditionRule(field="host.os_version", operator="exists")
    assert RuleEvaluator.evaluate_condition(sample_canonical_event, cond_missing) is False


def test_rule_condition_equals(sample_canonical_event: CanonicalEvent) -> None:
    """Test 'equals' operator."""
    cond = ConditionRule(field="network.protocol", operator="equals", value="dns")
    assert RuleEvaluator.evaluate_condition(sample_canonical_event, cond) is True

    cond_wrong = ConditionRule(field="network.protocol", operator="equals", value="http")
    assert RuleEvaluator.evaluate_condition(sample_canonical_event, cond_wrong) is False


def test_rule_condition_in_list(sample_canonical_event: CanonicalEvent) -> None:
    """Test 'in_list' operator."""
    cond = ConditionRule(field="source.ip", operator="in_list", value=["10.100.1.5", "10.100.1.6"])
    assert RuleEvaluator.evaluate_condition(sample_canonical_event, cond) is True

    cond_not_in = ConditionRule(field="source.ip", operator="in_list", value=["192.168.1.1"])
    assert RuleEvaluator.evaluate_condition(sample_canonical_event, cond_not_in) is False


def test_rule_condition_regex_match(sample_canonical_event: CanonicalEvent) -> None:
    """Test 'regex_match' operator."""
    cond = ConditionRule(field="destination.domain", operator="regex_match", value=r"evil-.*\.com")
    assert RuleEvaluator.evaluate_condition(sample_canonical_event, cond) is True

    cond_no_match = ConditionRule(
        field="destination.domain", operator="regex_match", value=r"^safe-.*"
    )
    assert RuleEvaluator.evaluate_condition(sample_canonical_event, cond_no_match) is False


def test_rule_evaluator_tenant_scoping(sample_canonical_event: CanonicalEvent) -> None:
    """Verify rule triggers only for authorized tenants."""
    rule_alpha_only = EnrichmentRuleConfig(
        rule_id="rule-alpha",
        tenant_scope=["tenant_alpha"],
        conditions=[ConditionRule(field="source.ip", operator="exists")],
        providers=["asset-local-cmdb"],
    )

    # Should match for tenant_alpha
    assert (
        RuleEvaluator.evaluate_rule(sample_canonical_event, rule_alpha_only, "tenant_alpha") is True
    )
    # Should not match for tenant_beta
    assert (
        RuleEvaluator.evaluate_rule(sample_canonical_event, rule_alpha_only, "tenant_beta") is False
    )


def test_rule_evaluator_disabled_rule(sample_canonical_event: CanonicalEvent) -> None:
    """Verify disabled rule never evaluates to True."""
    rule = EnrichmentRuleConfig(
        rule_id="disabled-rule",
        enabled=False,
        conditions=[ConditionRule(field="source.ip", operator="exists")],
        providers=["asset-local-cmdb"],
    )
    assert RuleEvaluator.evaluate_rule(sample_canonical_event, rule, "tenant_alpha") is False
