import logging
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status

from app.core.auth import Principal, get_current_principal

logger = logging.getLogger(__name__)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "grower": frozenset(
        {
            "auth:session",
            "farms:read",
            "farms:write",
            "lots:read",
            "events:read",
            "events:create",
            "products:read",
        }
    ),
    "cooperative": frozenset(
        {"auth:session", "lots:read", "events:read", "events:create", "products:read"}
    ),
    "transporter": frozenset(
        {"auth:session", "lots:read", "events:read", "events:create", "products:read"}
    ),
    "distributor": frozenset(
        {"auth:session", "lots:read", "events:read", "events:create", "products:read"}
    ),
    "inspector": frozenset(
        {"auth:session", "lots:read_all", "events:read_all", "products:read_all"}
    ),
    "organization_admin": frozenset(
        {
            "auth:session",
            "farms:read",
            "farms:write",
            "lots:read",
            "events:read",
            "events:create",
            "products:read",
        }
    ),
    "system_admin": frozenset({"auth:session", "products:read", "products:write"}),
}


def has_permission(role: str, permission: str) -> bool:
    permissions = ROLE_PERMISSIONS.get(role, frozenset())
    if permission in permissions:
        return True
    if permission == "lots:read" and "lots:read_all" in permissions:
        return True
    if permission == "events:read" and "events:read_all" in permissions:
        return True
    if permission == "products:read" and "products:read_all" in permissions:
        return True
    return False


def require_permission(
    permission: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declare the permission a business API route requires."""

    def decorator(endpoint: Callable[..., Any]) -> Callable[..., Any]:
        endpoint.__required_permission__ = permission  # type: ignore[attr-defined]
        return endpoint

    return decorator


def enforce_route_permission(
    request: Request,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> None:
    path = request.url.path
    method = request.method

    request.state.principal = principal
    request.state.organization_id = principal.organization_id

    # Tự động gán quyền dựa theo đường dẫn API (bền vững, không sợ bị mất wrapper decorator)
    permission = None
    if "/api/v1/products" in path:
        permission = (
            "products:write" if method in ["POST", "PUT", "DELETE"] else "products:read"
        )
    elif "/api/v1/farms" in path:
        permission = (
            "farms:write" if method in ["POST", "PUT", "DELETE"] else "farms:read"
        )
    elif "/api/v1/lots" in path:
        permission = (
            "lots:write" if method in ["POST", "PUT", "DELETE"] else "lots:read"
        )
    elif "/api/v1/events" in path:
        permission = (
            "events:write" if method in ["POST", "PUT", "DELETE"] else "events:read"
        )
    else:
        # Fallback kiểm tra qua thuộc tính endpoint cũ nếu có
        route = request.scope.get("route")
        endpoint = getattr(route, "endpoint", None)
        current = endpoint
        while current is not None:
            permission = getattr(current, "__required_permission__", None)
            if permission is not None:
                break
            current = getattr(current, "__wrapped__", None)

    if permission is None:
        logger.warning(
            "Denied API route without a declared permission "
            "user_id=%s organization_id=%s method=%s path=%s",
            principal.user_id,
            principal.organization_id,
            request.method,
            request.url.path,
            extra={"event": "authorization.route_missing_permission"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Quyền truy cập của API chưa được cấu hình.",
        )

    if not has_permission(principal.role, permission):
        logger.warning(
            "Denied API route due to insufficient permission "
            "user_id=%s organization_id=%s role=%s permission=%s method=%s path=%s",
            principal.user_id,
            principal.organization_id,
            principal.role,
            permission,
            request.method,
            request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền thực hiện thao tác này.",
        )
