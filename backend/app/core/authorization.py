from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status

from app.core.auth import Principal, get_current_principal
from app.core.security_events import log_security_event

# Permission that lifts tenant scoping for read-only access across
# organizations. Granted to `inspector` (and to `system_admin`); it never
# implies write access, so an inspector stays read-only.
CROSS_TENANT_READ_PERMISSIONS = frozenset({"lots:read_all"})

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "grower": frozenset(
        {
            "farms:read",
            "farms:write",
            "lots:read",
            "lots:write",
            "products:read",
            "products:write",
            "shipments:read",
            "shipments:create",
            "shipments:receive",
            "sensors:write",
            "cold_chain:read",
            "cold_chain:resolve",
        }
    ),
    "cooperative": frozenset(
        {
            "lots:read",
            "lots:write",
            "products:read",
            "products:write",
            "shipments:read",
            "shipments:create",
            "shipments:receive",
        }
    ),
    "transporter": frozenset(
        {
            "lots:read",
            "products:read",
            "shipments:read",
            "shipments:create",
            "shipments:receive",
            "sensors:read",
            "sensors:write",
            "cold_chain:read",
            "cold_chain:resolve",
        }
    ),
    "distributor": frozenset(
        {
            "lots:read",
            "lots:write",
            "products:read",
            "products:write",
            "shipments:read",
            "shipments:create",
            "shipments:receive",
            "cold_chain:read",
        }
    ),
    "inspector": frozenset(
        {
            "lots:read",
            "lots:read_all",
            "products:read",
            "shipments:read",
            "cold_chain:read",
        }
    ),
    "organization_admin": frozenset(
        {"farms:read", "farms:write", "lots:read", "products:read", "users:manage"}
    ),
    "system_admin": frozenset(
        {"organizations:manage", "users:manage", "lots:read_all"}
    ),
}


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def has_any_permission(principal: Principal, permissions: frozenset[str]) -> bool:
    return any(has_permission(principal.role, permission) for permission in permissions)


def can_read_across_organizations(principal: Principal) -> bool:
    """Whether the principal may read tenant-owned rows of other organizations."""
    return has_any_permission(principal, CROSS_TENANT_READ_PERMISSIONS)


def is_inspection_principal(principal: Principal) -> bool:
    """Inspection role: read-only oversight across organizations.

    Kept as an explicit predicate so the role name appears once. Inspection is
    read-only by construction: the role's permission set contains no write
    permission, so this can only ever widen visibility, never mutate data.
    """
    return principal.role == "inspector"


def require_permission(
    permission: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declare the permission an API route requires; undeclared routes are denied."""

    def decorator(endpoint: Callable[..., Any]) -> Callable[..., Any]:
        endpoint.__required_permission__ = permission  # type: ignore[attr-defined]
        return endpoint

    return decorator


def enforce_route_permission(
    request: Request,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> None:
    route = request.scope.get("route")
    endpoint = getattr(route, "endpoint", None)
    permission = getattr(endpoint, "__required_permission__", None)

    request.state.principal = principal
    request.state.organization_id = principal.organization_id

    if permission is None:
        log_security_event(
            "authorization.route_missing_permission",
            request=request,
            user_id=str(principal.user_id),
            organization_id=str(principal.organization_id),
            role=principal.role,
            endpoint=getattr(endpoint, "__module__", None),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Quyền truy cập của API chưa được cấu hình.",
        )

    if not has_permission(principal.role, permission):
        log_security_event(
            "authorization.permission_denied",
            request=request,
            user_id=str(principal.user_id),
            organization_id=str(principal.organization_id),
            role=principal.role,
            permission=permission,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền thực hiện thao tác này.",
        )
