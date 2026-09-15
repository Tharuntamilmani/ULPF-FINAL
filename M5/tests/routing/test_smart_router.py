"""
Routing tests for SmartRouter.
Verifies policy matching, multi-destination aggregation, priority ordering,
enabled/disabled policy states, and tenant-specific routing isolation.
"""
from app.router.router import SmartRouter
from app.router.rules import PolicyRule


def test_smart_router_matching():
    router = SmartRouter()

    rule_high = PolicyRule(
        id="critical-sec-rule",
        priority=100,
        enabled=True,
        when={
            "all": [
                {"field": "event.severity.value", "operator": ">=", "value": 4},
                {"field": "security.is_security_event", "operator": "==", "value": True}
            ]
        },
        destinations=["siem", "data_lake", "ai_stream"]
    )

    rule_mid = PolicyRule(
        id="general-auth-rule",
        priority=50,
        enabled=True,
        when={"field": "event.type", "operator": "==", "value": "authentication"},
        destinations=["siem"]
    )

    rule_disabled = PolicyRule(
        id="disabled-rule",
        priority=999,
        enabled=False,
        when={"field": "event.type", "operator": "==", "value": "authentication"},
        destinations=["http_webhook"]
    )

    router.set_rules([rule_mid, rule_high, rule_disabled])

    # Test event matching critical rule
    sec_event = {
        "event": {
            "id": "evt_sec_001",
            "type": "authentication",
            "severity": {"value": 5}
        },
        "security": {"is_security_event": True}
    }

    dests, decision = router.route(sec_event)

    assert "critical-sec-rule" in decision.matched_policies
    assert "general-auth-rule" in decision.matched_policies
    assert "disabled-rule" not in decision.matched_policies  # Disabled rule skipped!
    assert "siem" in dests
    assert "data_lake" in dests
    assert "ai_stream" in dests
    assert "http_webhook" not in dests
    assert decision.event_id == "evt_sec_001"


def test_tenant_specific_routing():
    router = SmartRouter()

    global_rule = PolicyRule(
        id="global-rule",
        priority=10,
        destinations=["data_lake"]
    )

    alpha_rule = PolicyRule(
        id="alpha-rule",
        priority=80,
        tenant_id="tenant_alpha",
        when={"field": "event.severity.value", "operator": ">=", "value": 3},
        destinations=["ai_stream"]
    )

    router.set_rules([global_rule, alpha_rule])

    # Event belonging to tenant_alpha
    alpha_event = {
        "event": {"id": "evt_alpha_01", "severity": {"value": 4}},
        "tenant": {"id": "tenant_alpha"}
    }
    dests_alpha, decision_alpha = router.route(alpha_event)
    assert "alpha-rule" in decision_alpha.matched_policies
    assert "global-rule" in decision_alpha.matched_policies
    assert "ai_stream" in dests_alpha
    assert "data_lake" in dests_alpha

    # Event belonging to tenant_beta
    beta_event = {
        "event": {"id": "evt_beta_01", "severity": {"value": 4}},
        "tenant": {"id": "tenant_beta"}
    }
    dests_beta, decision_beta = router.route(beta_event)
    assert "alpha-rule" not in decision_beta.matched_policies
    assert "global-rule" in decision_beta.matched_policies
    assert "ai_stream" not in dests_beta
    assert "data_lake" in dests_beta
