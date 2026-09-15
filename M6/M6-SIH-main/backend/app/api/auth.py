"""
Authentication API.
POST /api/v1/auth/login  — issue JWT with tenant context
GET  /api/v1/auth/me     — return current user
POST /api/v1/auth/users  — create user (SUPER_ADMIN or TENANT_ADMIN for their tenant)
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordRequestForm

from backend.app.audit.audit_service import AuditService
from backend.app.core.dependencies import DepDB, dep_current_user
from backend.app.core.logging import actor_var
from backend.app.core.rbac import ADMIN, SUPER_ADMIN, TENANT_ADMIN, require_roles
from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.core.tenant_context import DepTenantContext
from backend.app.models.audit_log import AuditAction
from backend.app.models.tenant import TenantStatus
from backend.app.repositories.tenant_repo import TenantRepository
from backend.app.repositories.user_repo import UserRepository
from backend.app.schemas.auth import TokenResponse, UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/auth")


@router.post("/login", response_model=TokenResponse)
async def login(
    db: DepDB,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    """Authenticate and return a JWT access token with tenant context."""
    repo = UserRepository(db)
    user = await repo.get_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # If tenant-scoped user, check tenant status
    if user.tenant_id:
        tenant = await TenantRepository(db).get(user.tenant_id)
        if not tenant or tenant.status != TenantStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant account is suspended or disabled",
            )

    primary_role = user.role_names[0] if user.role_names else None
    extra_claims = {
        "roles": user.role_names,
        "tenant_id": user.tenant_id,
        "role": primary_role,
    }
    token = create_access_token(subject=user.id, extra_claims=extra_claims)

    # Audit
    actor_var.set(user.username)
    audit = AuditService(db)
    await audit.record(
        actor=user.username,
        actor_role=primary_role,
        action=AuditAction.USER_LOGIN,
        resource_type="user",
        resource_id=user.username,
        tenant_id=user.tenant_id,
    )

    from backend.app.core.config import get_settings

    settings = get_settings()
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        tenant_id=user.tenant_id,
        role=primary_role,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[object, Depends(dep_current_user)],
) -> UserResponse:
    """Return the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: DepDB,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> UserResponse:
    """Create a new user (SUPER_ADMIN or TENANT_ADMIN for own tenant)."""
    repo = UserRepository(db)
    tenant_repo = TenantRepository(db)

    is_super = getattr(current_user, "is_super_admin", False) or getattr(
        current_user, "is_superuser", False
    )
    caller_tenant_id = getattr(current_user, "tenant_id", None)

    target_tenant_id: str | None
    if is_super:
        target_tenant_id = data.tenant_id
        if target_tenant_id:
            tenant = await tenant_repo.get(target_tenant_id)
            if not tenant:
                tenant = await tenant_repo.get_by_slug(target_tenant_id)
            if not tenant:
                raise HTTPException(
                    status_code=404, detail=f"Tenant '{target_tenant_id}' not found"
                )
            target_tenant_id = tenant.id
    else:
        # Tenant Admin can only create users in their own tenant
        if not caller_tenant_id:
            raise HTTPException(status_code=403, detail="Tenant admin must belong to a tenant")
        if data.tenant_id and data.tenant_id != caller_tenant_id:
            raise HTTPException(status_code=403, detail="Cannot create user in another tenant")
        target_tenant_id = caller_tenant_id

        # Tenant Admin cannot create SUPER_ADMIN or ADMINISTRATOR
        if data.role in {SUPER_ADMIN, ADMIN}:
            raise HTTPException(
                status_code=403, detail="Tenant admin cannot grant platform admin roles"
            )

    # Check uniqueness
    if await repo.get_by_username(data.username):
        raise HTTPException(status_code=409, detail=f"Username '{data.username}' is taken")
    if await repo.get_by_email(data.email):
        raise HTTPException(status_code=409, detail=f"Email '{data.email}' is registered")

    user = await repo.create(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        tenant_id=target_tenant_id,
        is_superuser=False,
    )

    # Assign role
    role = await repo.get_role_by_name(data.role)
    if not role:
        role = await repo.create_role(data.role)
    await repo.assign_role(user.id, role.id)

    # Audit
    audit = AuditService(db)
    await audit.record(
        actor=getattr(current_user, "username", "unknown"),
        actor_role=getattr(current_user, "role_names", ["UNKNOWN"])[0]
        if getattr(current_user, "role_names", None)
        else None,
        action=AuditAction.USER_CREATED,
        resource_type="user",
        resource_id=user.username,
        tenant_id=target_tenant_id,
    )

    # Reload with roles
    user = await repo.get_by_id(user.id)  # type: ignore[assignment]
    return UserResponse.model_validate(user)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
    skip: int = 0,
    limit: int = 50,
) -> list[UserResponse]:
    """List users scoped to tenant (or platform-wide for SUPER_ADMIN)."""
    repo = UserRepository(db)
    users = await repo.list_users(tenant_id=ctx.tenant_id, skip=skip, limit=limit)
    return [UserResponse.model_validate(u) for u in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> UserResponse:
    """Get user by ID with tenant scope check."""
    repo = UserRepository(db)
    if ctx.is_super_admin:
        user = await repo.get_by_id(user_id)
    else:
        user = await repo.get_by_id_and_tenant(user_id, ctx.require_tenant_id())
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    data: UserUpdate,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> UserResponse:
    """Update user with strict tenant check (tenant reassignment is super admin only)."""
    repo = UserRepository(db)
    if ctx.is_super_admin:
        user = await repo.get_by_id(user_id)
    else:
        user = await repo.get_by_id_and_tenant(user_id, ctx.require_tenant_id())
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_dict: dict[str, Any] = {}
    if data.email is not None:
        existing = await repo.get_by_email(data.email)
        if existing and existing.id != user.id:
            raise HTTPException(status_code=409, detail="Email already taken")
        update_dict["email"] = data.email
    if data.password is not None:
        update_dict["hashed_password"] = hash_password(data.password)
    if data.is_active is not None:
        update_dict["is_active"] = data.is_active

    # Tenant reassignment is a privileged platform operation
    if data.tenant_id is not None:
        if not ctx.is_super_admin:
            raise HTTPException(
                status_code=403,
                detail="Tenant reassignment is a privileged platform operation",
            )
        update_dict["tenant_id"] = data.tenant_id

    if data.role is not None:
        if not ctx.is_super_admin and data.role in {SUPER_ADMIN, ADMIN}:
            raise HTTPException(
                status_code=403,
                detail="Tenant admin cannot grant platform admin roles",
            )
        await repo.clear_roles(user.id)
        role = await repo.get_role_by_name(data.role)
        if not role:
            role = await repo.create_role(data.role)
        await repo.assign_role(user.id, role.id)

    if update_dict:
        user = await repo.update(user, update_dict)

    audit = AuditService(db)
    await audit.record(
        actor=getattr(current_user, "username", "unknown"),
        actor_role=getattr(current_user, "role_names", ["UNKNOWN"])[0]
        if getattr(current_user, "role_names", None)
        else None,
        action=AuditAction.USER_UPDATED,
        resource_type="user",
        resource_id=user.username,
        tenant_id=user.tenant_id,
    )
    refreshed_user = await repo.get_by_id(user.id)
    if refreshed_user is None:
        raise HTTPException(status_code=404, detail="User not found after update")
    return UserResponse.model_validate(refreshed_user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: DepDB,
    ctx: DepTenantContext,
    current_user: Annotated[object, Depends(require_roles(SUPER_ADMIN, ADMIN, TENANT_ADMIN))],
) -> Response:
    """Delete user with tenant scope check."""
    repo = UserRepository(db)
    if ctx.is_super_admin:
        user = await repo.get_by_id(user_id)
    else:
        user = await repo.get_by_id_and_tenant(user_id, ctx.require_tenant_id())
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == getattr(current_user, "id", None):
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    username = user.username
    tenant_id = user.tenant_id
    await repo.delete(user)

    audit = AuditService(db)
    await audit.record(
        actor=getattr(current_user, "username", "unknown"),
        actor_role=getattr(current_user, "role_names", ["UNKNOWN"])[0]
        if getattr(current_user, "role_names", None)
        else None,
        action=AuditAction.USER_DELETED,
        resource_type="user",
        resource_id=username,
        tenant_id=tenant_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
