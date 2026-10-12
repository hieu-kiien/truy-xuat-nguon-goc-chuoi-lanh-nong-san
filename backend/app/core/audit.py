"""Central request auditing, atomic with business commits where they occur.

The middleware never reads bodies or copies headers. Transaction hooks capture
generated object IDs and append the audit in the same outer transaction.
Rejected requests without a business commit get a separate runtime-role append.
"""

import logging
from contextvars import ContextVar
from dataclasses import dataclass
from ipaddress import ip_address
from uuid import UUID, uuid4

from sqlalchemy import event, insert
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request

from app.core.auth import Principal, extract_session_token
from app.core.database import SessionLocal, set_db_context
from app.core.security import hash_session_token
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)
TABLES = {
    "lots": "lot",
    "farms": "farm",
    "products": "product",
    "locations": "location",
    "handovers": "handover",
    "events": "event",
    "auth": "user",
    "imports": "import",
}
SUBACTIONS = {
    "login",
    "logout",
    "split",
    "merge",
    "consume",
    "move",
    "accept",
    "reject",
    "verify",
}


@dataclass
class AuditContext:
    scope: dict
    id: UUID
    action: str
    object_type: str
    object_id: UUID | None = None
    created_id: UUID | None = None
    pending: bool = False
    persisted: bool = False


current_audit: ContextVar[AuditContext | None] = ContextVar(
    "current_audit", default=None
)


def _context(scope: dict) -> AuditContext:
    parts = scope["path"].strip("/").split("/")[2:]
    resource = parts[0] if parts and parts[0] in TABLES else "api"
    subaction = (
        parts[-1]
        if parts and parts[-1] in SUBACTIONS
        else {"POST": "create", "PUT": "update", "PATCH": "update", "DELETE": "delete"}[
            scope["method"]
        ]
    )
    if resource == "imports":
        subaction = "farms" if parts[-1] == "farms" else "products"
    object_id = None
    for part in parts:
        try:
            object_id = UUID(part)
            break
        except ValueError:
            pass
    if resource == "events" and parts[-1] == "integrity-checks":
        return AuditContext(scope, uuid4(), "lots.integrity_check", "lot", object_id)
    return AuditContext(
        scope,
        uuid4(),
        f"{resource}.{subaction}",
        TABLES.get(resource, "request"),
        object_id,
    )


def _row(context: AuditContext, status: int) -> AuditLog:
    state = context.scope.get("state", {})
    principal = state.get("principal")
    if isinstance(principal, Principal):
        actor = {
            "user_id": principal.user_id,
            "full_name": principal.full_name,
            "organization_id": principal.organization_id,
            "organization_name": principal.organization_name,
        }
    else:
        actor = state.get("audit_actor", {})
    outcome = "success" if status < 400 else "error" if status >= 500 else "denied"
    reasons = {
        401: "credentials_rejected"
        if context.action == "auth.login"
        else "unauthenticated",
        403: "permission_denied",
        404: "not_found",
        409: "conflict",
        422: "validation_failed",
    }
    try:
        client_ip = str(ip_address(context.scope.get("client", (None, 0))[0]))
    except (ValueError, TypeError):
        client_ip = None
    object_id = context.object_id or context.created_id
    if context.object_type == "user":
        object_id = actor.get("user_id")
    return AuditLog(
        id=context.id,
        actor_user_id=actor.get("user_id"),
        actor_name=actor.get("full_name"),
        actor_authenticated=bool(actor)
        and (context.action != "auth.login" or status < 400),
        organization_id=actor.get("organization_id"),
        organization_name=actor.get("organization_name"),
        client_ip=client_ip,
        action=context.action,
        object_type=context.object_type,
        object_id=object_id,
        outcome=outcome,
        status_code=status,
        reason=None
        if status < 400
        else reasons.get(
            status, "internal_error" if status >= 500 else "request_rejected"
        ),
    )


@event.listens_for(SessionLocal, "after_flush")
def capture_created_id(db, flush_context):
    context = current_audit.get()
    if (
        not context
        or context.object_id
        or context.created_id
        or db.info.get("audit_fallback")
    ):
        return
    for item in db.new:
        if TABLES.get(item.__tablename__) == context.object_type and not isinstance(
            item, AuditLog
        ):
            context.created_id = item.id
            break


@event.listens_for(SessionLocal, "before_commit")
def append_transaction_audit(db):
    context = current_audit.get()
    if (
        not context
        or context.pending
        or context.persisted
        or db.in_nested_transaction()
        or db.info.get("audit_fallback")
    ):
        return
    state = context.scope.get("state", {})
    if not state.get("principal") and not state.get("audit_actor"):
        return
    route = context.scope.get("route")
    status = state.get("audit_status", getattr(route, "status_code", None) or 200)
    if context.action == "auth.logout":
        # Preserve the authenticated RLS context before revoking its session.
        # This flush is still inside the same transaction as the revocation.
        row = _row(context, status)
        db.execute(
            insert(AuditLog.__table__).values(
                **{
                    key: value
                    for key, value in row.__dict__.items()
                    if not key.startswith("_")
                }
            )
        )
        context.pending = True
        return
    db.flush()
    db.add(_row(context, status))
    context.pending = True


@event.listens_for(SessionLocal, "after_commit")
def mark_audit_committed(db):
    context = current_audit.get()
    if context and context.pending and not db.in_nested_transaction():
        context.persisted = True
        context.pending = False


@event.listens_for(SessionLocal, "after_rollback")
def discard_rolled_back_audit(db):
    context = current_audit.get()
    if context and not db.in_nested_transaction():
        context.pending = False
        context.created_id = None


def _fallback(context: AuditContext, status: int) -> bool:
    try:
        with SessionLocal() as db:
            db.info["audit_fallback"] = True
            token = extract_session_token(Request(context.scope))
            if token:
                set_db_context(db, session_token_hash=hash_session_token(token))
            email = context.scope.get("state", {}).get("audit_login_email")
            if email:
                set_db_context(db, login_email=email)
            db.add(_row(context, status))
            db.commit()
        context.persisted = True
        return True
    except Exception as error:
        # Deliberately omit exception text/traceback: drivers can include parameters.
        logger.error(
            "Audit persistence failed request_id=%s action=%s exception_type=%s",
            context.id,
            context.action,
            type(error).__name__,
        )
        return False


class AuditMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope.get("method") not in {"POST", "PUT", "PATCH", "DELETE"}
            or not scope["path"].startswith("/api/v1/")
        ):
            return await self.app(scope, receive, send)
        context = _context(scope)
        marker = current_audit.set(context)

        async def audit_send(message):
            if message["type"] == "http.response.start":
                if not context.persisted:
                    await run_in_threadpool(_fallback, context, message["status"])
                message = {
                    **message,
                    "headers": [
                        *message.get("headers", []),
                        (b"x-request-id", str(context.id).encode("ascii")),
                    ],
                }
            await send(message)

        try:
            await self.app(scope, receive, audit_send)
        except Exception as error:
            if not context.persisted:
                await run_in_threadpool(_fallback, context, 500)
            else:
                logger.error(
                    "Response failed after audited commit request_id=%s exception_type=%s",
                    context.id,
                    type(error).__name__,
                )
            raise
        finally:
            current_audit.reset(marker)
