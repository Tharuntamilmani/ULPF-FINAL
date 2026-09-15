"""
Policy collection and configuration container models.
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from app.router.rules import PolicyRule


class TenantPolicyOverride(BaseModel):
    tenant_id: str
    policies: List[PolicyRule] = Field(default_factory=list)


class PolicyConfigFile(BaseModel):
    version: str = "1.0"
    policies: List[PolicyRule] = Field(default_factory=list)
    tenant_policies: Optional[List[TenantPolicyOverride]] = None
