"""
Policy Engine providing management, reloading, and routing facade.
"""
from typing import Any, Dict, List, Optional, Tuple
from app.policy.loader import PolicyLoader
from app.router.rules import PolicyRule, RoutingDecision
from app.router.router import SmartRouter


class PolicyEngine:
    """
    Policy Engine owns runtime policy rules management and evaluation delegating to SmartRouter.
    """

    def __init__(self, policy_file_path: Optional[str] = None):
        self.policy_file_path = policy_file_path
        self.router = SmartRouter()
        if policy_file_path:
            self.reload_policies()

    def load_rules(self, rules: List[PolicyRule]) -> None:
        """
        Set active policy rules.
        """
        self.router.set_rules(rules)

    def reload_policies(self) -> List[PolicyRule]:
        """
        Reload policies from configured YAML policy file.
        Gracefully falls back to default fallback policy if file not found.
        """
        if not self.policy_file_path:
            raise ValueError("No policy file path specified for reload")
        import os
        import logging
        if not os.path.exists(self.policy_file_path):
            logging.getLogger("PolicyEngine").warning(
                f"Policy file '{self.policy_file_path}' not found. Initializing default fallback rule."
            )
            fallback_rule = PolicyRule(
                id="default_fallback_policy",
                priority=1,
                destinations=["siem", "data_lake"]
            )
            self.load_rules([fallback_rule])
            return [fallback_rule]

        rules = PolicyLoader.load_from_file(self.policy_file_path)
        self.load_rules(rules)
        return rules


    def evaluate(self, event: Dict[str, Any]) -> Tuple[List[str], RoutingDecision]:
        """
        Evaluate policy rules for an incoming UES event.
        Returns target destination names and routing decision audit log.
        """
        return self.router.route(event)

    def list_policies(self) -> List[PolicyRule]:
        """
        List currently active policies.
        """
        return self.router.rules
