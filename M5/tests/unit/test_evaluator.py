"""
Unit tests for ULPF M5 Policy Evaluator.
Validates nested field extraction, comparison operators (including type coercion),
and condition evaluation with nested 'all' (AND) and 'any' (OR) structures.
"""
from app.router.evaluator import extract_field_value, compare_values, evaluate_condition
from app.router.rules import Condition


def test_extract_field_value():
    sample_event = {
        "event": {
            "id": "evt_unit_01",
            "type": "authentication",
            "severity": {"value": 4, "label": "high"}
        },
        "tenant": {"id": "tenant_alpha"},
        "source": {"ip": "10.0.0.5"}
    }

    assert extract_field_value(sample_event, "event.id") == "evt_unit_01"
    assert extract_field_value(sample_event, "event.severity.value") == 4
    assert extract_field_value(sample_event, "tenant.id") == "tenant_alpha"
    assert extract_field_value(sample_event, "source.ip") == "10.0.0.5"
    assert extract_field_value(sample_event, "non.existent.path") is None
    assert extract_field_value(None, "event.id") is None
    assert extract_field_value(sample_event, "") is None


def test_compare_values():
    # Equality with type coercion
    assert compare_values(4, "==", 4) is True
    assert compare_values(4, "==", "4") is True
    assert compare_values("4", "==", 4) is True
    assert compare_values(True, "==", True) is True
    assert compare_values(True, "==", "true") is True
    assert compare_values("True", "==", True) is True
    assert compare_values(False, "==", "false") is True
    assert compare_values(5, "!=", 4) is True
    assert compare_values("admin", "==", "admin") is True

    # Numeric comparisons
    assert compare_values(4, ">=", 4) is True
    assert compare_values(5, ">=", 4) is True
    assert compare_values(3, ">=", 4) is False
    assert compare_values("5", ">", 4) is True
    assert compare_values(2, "<=", 2) is True
    assert compare_values(1, "<", 2) is True

    # List membership (in)
    assert compare_values("auth", "in", ["auth", "login"]) is True
    assert compare_values("payment", "in", ["auth", "login"]) is False
    assert compare_values("admin", "in", "administrator") is True

    # Contains
    assert compare_values(["siem", "datalake"], "contains", "siem") is True
    assert compare_values("secure_login_event", "contains", "login") is True

    # Regex matching
    assert compare_values("192.168.1.100", "matches", r"^192\.168\.") is True
    assert compare_values("10.0.0.1", "matches", r"^192\.168\.") is False

    # None handling
    assert compare_values(None, ">=", 4) is False
    assert compare_values(None, "==", None) is True
    assert compare_values(4, "==", None) is False


def test_evaluate_condition_single():
    event = {
        "event": {
            "id": "evt_test_01",
            "type": "network_attack",
            "severity": {"value": 5}
        },
        "security": {"is_security_event": True}
    }

    # Direct condition dict
    cond1 = {"field": "event.severity.value", "operator": ">=", "value": 4}
    assert evaluate_condition(event, cond1) is True

    cond2 = {"field": "event.type", "operator": "==", "value": "network_attack"}
    assert evaluate_condition(event, cond2) is True

    cond3 = {"field": "event.severity.value", "operator": "<", "value": 3}
    assert evaluate_condition(event, cond3) is False

    # Condition object
    cond_obj = Condition(field="security.is_security_event", operator="==", value=True)
    assert evaluate_condition(event, cond_obj) is True


def test_evaluate_condition_nested_all_any():
    event = {
        "event": {
            "id": "evt_nested_01",
            "type": "auth_failure",
            "severity": {"value": 4}
        },
        "source": {"ip": "198.51.100.22"},
        "security": {"is_security_event": True}
    }

    # 'all' (AND logic)
    all_cond = {
        "all": [
            {"field": "event.severity.value", "operator": ">=", "value": 3},
            {"field": "security.is_security_event", "operator": "==", "value": True}
        ]
    }
    assert evaluate_condition(event, all_cond) is True

    all_cond_fail = {
        "all": [
            {"field": "event.severity.value", "operator": ">=", "value": 5},
            {"field": "security.is_security_event", "operator": "==", "value": True}
        ]
    }
    assert evaluate_condition(event, all_cond_fail) is False

    # 'any' (OR logic)
    any_cond = {
        "any": [
            {"field": "event.severity.value", "operator": ">=", "value": 5},
            {"field": "event.type", "operator": "==", "value": "auth_failure"}
        ]
    }
    assert evaluate_condition(event, any_cond) is True

    # Nested combination
    nested = {
        "all": [
            {"field": "security.is_security_event", "operator": "==", "value": True},
            {
                "any": [
                    {"field": "event.type", "operator": "==", "value": "auth_failure"},
                    {"field": "event.severity.value", "operator": "==", "value": 5}
                ]
            }
        ]
    }
    assert evaluate_condition(event, nested) is True
