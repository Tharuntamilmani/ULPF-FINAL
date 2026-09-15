from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class Role(str, Enum):
    INGEST = "ingest"
    ANALYST = "analyst"
    STUDIO = "studio"
    ADMIN = "admin"


class AuthContext(BaseModel):
    """Represents trusted authenticated identity and role claims from the control plane."""

    principal_id: str = Field(
        ..., description="Unique ID of authenticated subject/service"
    )
    tenant_id: str = Field(
        ..., description="Tenant ID to which this principal is scoped"
    )
    roles: List[str] = Field(default_factory=list, description="Assigned roles")
    is_system: bool = Field(
        False, description="Whether principal is a privileged system administrator"
    )

    def has_role(self, *required_roles: str) -> bool:
        if self.is_system or Role.ADMIN.value in self.roles:
            return True
        return any(r in self.roles for r in required_roles)

    def can_access_tenant(self, target_tenant_id: str) -> bool:
        if self.is_system:
            return True
        return self.tenant_id == target_tenant_id
