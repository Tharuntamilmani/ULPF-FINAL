"""
Policy file loader supporting YAML configuration parsing and tenant overrides.
"""
import os
import yaml
from typing import Any, List
from app.router.rules import PolicyRule


class PolicyLoader:
    """
    Loads delivery policies from YAML configuration files.
    """

    @staticmethod
    def load_from_file(file_path: str) -> List[PolicyRule]:
        """
        Load policy rules from a YAML file.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Policy file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)

        return PolicyLoader.load_from_dict(raw_data)

    @staticmethod
    def load_from_dict(raw_data: Any) -> List[PolicyRule]:
        """
        Parse raw YAML data into a list of PolicyRule objects.
        Merges global policies and tenant-specific policies.
        Gracefully handles both root list and dictionary formats.
        """
        rules: List[PolicyRule] = []

        if raw_data is None:
            return rules

        # If raw_data is directly a list of rules
        if isinstance(raw_data, list):
            for item in raw_data:
                if isinstance(item, dict):
                    try:
                        rules.append(PolicyRule(**item))
                    except Exception as e:
                        import logging
                        logging.getLogger("PolicyLoader").warning(f"Skipping invalid policy rule: {e}")
            return rules

        # Otherwise expect a dictionary
        if isinstance(raw_data, dict):
            # Check for direct 'policies' or 'rules' key
            policy_list = raw_data.get("policies") or raw_data.get("rules") or []
            for item in policy_list:
                if isinstance(item, dict):
                    try:
                        rules.append(PolicyRule(**item))
                    except Exception as e:
                        import logging
                        logging.getLogger("PolicyLoader").warning(f"Skipping invalid policy rule: {e}")
                elif isinstance(item, PolicyRule):
                    rules.append(item)

            # Check for tenant_policies
            tenant_policies = raw_data.get("tenant_policies") or []
            for tenant_override in tenant_policies:
                if isinstance(tenant_override, dict):
                    t_id = tenant_override.get("tenant_id")
                    t_rules = tenant_override.get("policies") or []
                    for tr in t_rules:
                        if isinstance(tr, dict):
                            try:
                                r = PolicyRule(**tr)
                                if not r.tenant_id:
                                    r.tenant_id = t_id
                                rules.append(r)
                            except Exception as e:
                                import logging
                                logging.getLogger("PolicyLoader").warning(f"Skipping invalid tenant policy rule: {e}")
                        elif isinstance(tr, PolicyRule):
                            if not tr.tenant_id:
                                tr.tenant_id = t_id
                            rules.append(tr)

        return rules

