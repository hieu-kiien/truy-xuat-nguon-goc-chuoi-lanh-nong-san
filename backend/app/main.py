import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.endpoints import auth, public_trace
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import get_db
from app.core.logging_config import configure_logging
from app.core.security_events import log_security_event

configure_logging()

DOCS_ENABLED = settings.APP_ENV == "development"

app = FastAPI(
    title="Cold Chain Traceability API",
    description="API hệ thống truy xuất nguồn gốc và giám sát chuỗi lạnh nông sản",
    version="1.0.0",
    docs_url="/docs" if DOCS_ENABLED else None,
    redoc_url="/redoc" if DOCS_ENABLED else None,
    openapi_url="/openapi.json" if DOCS_ENABLED else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
    # The session credential is an HttpOnly cookie and is never echoed back in
    # a response header, so nothing needs to be added to the CORS safelist.
    expose_headers=["X-Request-ID"],
)

# Every router below `/api/v1` is mounted with a declared public/protected
# policy. `api_router` carries `enforce_route_permission`, which denies any
# route that forgets `@require_permission`, so a business route cannot bypass
# authorization by being included in the wrong place.
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(public_trace.router, prefix="/api/v1/trace", tags=["public trace"])
app.include_router(api_router, prefix="/api/v1")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    if request.url.path.startswith("/api/v1/auth"):
        response.headers["Pragma"] = "no-cache"
    return response


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "message": "Backend service is online"}


@app.get("/health/live", tags=["health"])
def liveness_check():
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def readiness_check(db: Annotated[Session, Depends(get_db)]):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from error
    return {"status": "ready", "database": "ok"}


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> Response:
    """Log unexpected failures with the request id, never leak internals."""
    log_security_event(
        "app.unhandled_error",
        level=50,
        request=request,
        error_type=type(exc).__name__,
        detail=str(exc),
    )
    return Response(
        content='{"detail":"Internal server error."}',
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        media_type="application/json",
    )
