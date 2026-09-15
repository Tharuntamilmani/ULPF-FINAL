"""
Pydantic models for Policy Rules, Conditions, and Routing Decisions.
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, AliasChoices


class Condition(BaseModel):
    field: Optional[str] = None
    operator: Optional[str] = None  # ==, !=, >=, <=, >, <, in, contains, matches
    value: Optional[Any] = None
    all: Optional[List["Condition"]] = None
    any: Optional[List["Condition"]] = None


# Support recursive condition models
Condition.model_rebuild()


class PolicyRule(BaseModel):
    id: str = Field(default="", validation_alias=AliasChoices("id", "policy_id"))
    priority: int = 1
    enabled: bool = True
    description: Optional[str] = None
    tenant_id: Optional[str] = None
    when: Optional[Union[Condition, dict, List[Any]]] = None
    destinations: List[str] = Field(default_factory=list)

    def __init__(self, **data: Any):
        # Support 'policy_id' as alias for 'id'
        if "policy_id" in data and "id" not in data:
            data["id"] = data["policy_id"]
        elif "id" not in data and "policy_id" not in data:
            data["id"] = "policy_unnamed"

        # Support 'conditions' as alias for 'when'
        if "conditions" in data and "when" not in data:
            data["when"] = data["conditions"]

        # If 'when' is a list, normalize to {'all': when}
        if isinstance(data.get("when"), list):
            data["when"] = {"all": data["when"]}

        super().__init__(**data)

    @property
    def policy_id(self) -> str:
        return self.id


class PolicySet(BaseModel):
    version: str = "1.0"
    policies: List[PolicyRule] = Field(default_factory=list)


class RoutingDecision(BaseModel):
    event_id: str
    matched_policies: List[str]
    destinations: List[str]
    evaluated_at: str
    tenant_id: Optional[str] = None
    delivery_status: Optional[Dict[str, Any]] = None

