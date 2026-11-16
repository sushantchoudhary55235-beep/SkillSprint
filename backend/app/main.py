"""SkillSprint API entrypoint."""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import api_router
from app.core.config import settings
from app.core.exceptions import SkillSprintError
from app.core.rate_limit import RateLimitExceededError, get_general_limiter

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("skillsprint")

# ------------------------------------------------------------------ config guard
# Phase 15 rule: never allow_origins=["*"] in production. The allowed origins
# always come from CORS_ORIGINS env (comma-separated) — a wildcard value is
# refused at startup in production so a misconfiguration cannot ship.
def validate_production_config(cfg) -> None:
    """Refuse to boot with unsafe production configuration.

    Extracted as a function so the guard is unit-testable without re-importing
    the app module (import-time checks run when this module is loaded).
    """
    if not cfg.is_production:
        return
    origins = cfg.cors_origins
    if not origins or "*" in origins:
        raise RuntimeError(
            "CORS_ORIGINS must list explicit production origins "
            "(comma-separated) when ENVIRONMENT=production — '*' is not allowed."
        )
    # Audit fix (M1): a default JWT secret in production means every token is
    # forgeable — the exact failure the CORS guard exists to prevent. Fail at
    # startup, mirroring the CORS rule, so a forgotten .env cannot ship.
    if cfg.JWT_SECRET_KEY in ("change-me-to-a-long-random-secret", "", "secret", "changeme"):
        raise RuntimeError(
            "JWT_SECRET_KEY must be set to a long random value when "
            "ENVIRONMENT=production — the default secret is not deployable."
        )


validate_production_config(settings)
_cors_origins = settings.cors_origins

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="Gamified AI-powered placement-readiness and personalized learning platform.",
    docs_url="/docs" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ------------------------------------------------------------------ general rate limiting (production only)
_general_limiter = get_general_limiter()

if _general_limiter is not None:
    @app.middleware("http")
    async def general_rate_limit_middleware(request: Request, call_next):
        # Skip rate limiting for health checks, docs, and AI endpoints (which have their own limiter)
        path = request.url.path
        if (path.startswith("/api/health") or 
            path.startswith("/api/ai") or
            path in ("/docs", "/openapi.json", "/redoc")):
            return await call_next(request)

        # Get user ID from auth header if present
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_access_token
                token = auth_header.split(" ", 1)[1]
                payload = decode_access_token(token)
                user_id = int(payload.get("sub", 0))
                if user_id > 0:
                    _general_limiter.check(user_id)
            except Exception:
                # Invalid token - let the auth dependency handle it
                pass

        return await call_next(request)

app.include_router(api_router, prefix="/api")


_ERROR_CODE_BY_STATUS = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_ERROR",
    status.HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
}


@app.exception_handler(RateLimitExceededError)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceededError) -> JSONResponse:
    """AI quota exhaustion returns 429 with the standard error envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.message, "error_code": exc.error_code},
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Route all HTTP errors (including 404) through the standard envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": str(exc.detail),
            "error_code": _ERROR_CODE_BY_STATUS.get(exc.status_code, "HTTP_ERROR"),
        },
    )


@app.exception_handler(SkillSprintError)
async def domain_exception_handler(request: Request, exc: SkillSprintError) -> JSONResponse:
    """Translate business-rule errors into the standard envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.message, "error_code": exc.error_code},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return the standard error envelope for validation failures (422)."""
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "message": "Validation error", "error_code": "VALIDATION_ERROR"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Never expose internal stack traces to clients (docs/API_Specification.md §25)."""
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "message": "Internal server error", "error_code": "INTERNAL_ERROR"},
    )
