"""
Policy evaluator logic for extracting UES fields and checking condition trees.
"""
import re
from typing import Any, Dict, List, Optional, Union
from app.router.rules import Condition


def extract_field_value(event: Dict[str, Any], path: str) -> Any:
    """
    Extract a nested field value from a dict using dot-notation (e.g., 'event.severity.value').
    Also supports top-level field checks like 'tenant_id' or 'event_id'.
    """
    if not path or not isinstance(event, dict):
        return None

    parts = path.split(".")
    current = event
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _to_bool(val: Any) -> Optional[bool]:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        if val.lower() in ("true", "1", "yes"):
            return True
        if val.lower() in ("false", "0", "no"):
            return False
    if isinstance(val, (int, float)):
        return bool(val)
    return None


def compare_values(actual: Any, operator: str, target: Any) -> bool:
    """
    Compare actual extracted value against target value using operator.
    Provides type-aware comparison handling stringified booleans and numbers.
    """
    if operator in ("==", "eq"):
        if actual is None and target is None:
            return True
        if actual is None or target is None:
            return False

        # Boolean comparison
        actual_bool = _to_bool(actual) if isinstance(actual, bool) or (isinstance(target, bool) and isinstance(actual, str)) else None
        target_bool = _to_bool(target) if isinstance(target, bool) or (isinstance(actual, bool) and isinstance(target, str)) else None
        if actual_bool is not None and target_bool is not None:
            return actual_bool == target_bool

        # Numeric comparison
        try:
            return float(actual) == float(target)
        except (ValueError, TypeError):
            pass

        # String or raw equality
        return actual == target or str(actual) == str(target)

    elif operator in ("!=", "neq"):
        return not compare_values(actual, "==", target)

    elif operator in (">=", "gte"):
        if actual is None or target is None:
            return False
        try:
            return float(actual) >= float(target)
        except (ValueError, TypeError):
            return False

    elif operator in ("<=", "lte"):
        if actual is None or target is None:
            return False
        try:
            return float(actual) <= float(target)
        except (ValueError, TypeError):
            return False

    elif operator in (">", "gt"):
        if actual is None or target is None:
            return False
        try:
            return float(actual) > float(target)
        except (ValueError, TypeError):
            return False

    elif operator in ("<", "lt"):
        if actual is None or target is None:
            return False
        try:
            return float(actual) < float(target)
        except (ValueError, TypeError):
            return False

    elif operator == "in":
        if target is None or actual is None:
            return False
        if isinstance(target, (list, tuple, set)):
            return any(compare_values(actual, "==", item) for item in target)
        if isinstance(target, str):
            return str(actual) in target
        return False

    elif operator == "contains":
        if actual is None or target is None:
            return False
        if isinstance(actual, (list, tuple, set)):
            return any(compare_values(item, "==", target) for item in actual)
        if isinstance(actual, str):
            return str(target) in actual
        return False

    elif operator in ("matches", "regex"):
        if actual is None or target is None:
            return False
        try:
            return bool(re.search(str(target), str(actual)))
        except (re.error, TypeError):
            return False

    return False


def evaluate_condition(event: Dict[str, Any], condition: Union[Condition, Dict[str, Any], List[Any]]) -> bool:
    """
    Evaluate a Condition, Dict, or list against a UES event dict.
    Supports nested 'all' (AND) and 'any' (OR) logic.
    """
    if isinstance(condition, list):
        return all(evaluate_condition(event, item) for item in condition)
    elif isinstance(condition, dict):
        cond_dict = condition
    elif isinstance(condition, Condition):
        cond_dict = condition.model_dump(exclude_none=True)
    else:
        return False

    # Check nested 'all'
    if "all" in cond_dict and cond_dict["all"]:
        nested_all = cond_dict["all"]
        return all(evaluate_condition(event, item) for item in nested_all)

    # Check nested 'any'
    if "any" in cond_dict and cond_dict["any"]:
        nested_any = cond_dict["any"]
        return any(evaluate_condition(event, item) for item in nested_any)

    # Check single condition
    field = cond_dict.get("field")
    operator = cond_dict.get("operator")
    target_value = cond_dict.get("value")

    if not field or not operator:
        return False

    actual_value = extract_field_value(event, field)
    return compare_values(actual_value, operator, target_value)

