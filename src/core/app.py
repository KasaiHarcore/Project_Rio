"""FastAPI application factory and lifecycle management.

Creates the main FastAPI app with:
- CORS middleware (config-driven)
- Request ID + timing middleware
- Lifespan handler (startup/shutdown hooks + concurrency pools)
- Structured exception handlers (AppException, validation, unhandled)
- v1 API router mounting
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.startup import run_startup_tasks, run_shutdown_tasks
from core.concurrency import concurrency_manager
from core.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    DuplicateError,
    ValidationError,
    WorkflowError,
    ExternalServiceError,
    RateLimitError,
    OAuthError,
)
from core.settings import get_cors_config
from utils.log import log_info, log_warning, log_error


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    log_info("FastAPI starting up...")
    run_startup_tasks()
    concurrency_manager.start()

    # Inject cache into singleton services that can't use FastAPI Depends
    try:
        from infrastructure.cache import cache_service
        from services.chat_history_service import chat_history_service
        chat_history_service.inject_cache(cache_service)
    except Exception as e:
        log_warning(f"Cache injection into ChatHistoryService failed: {e}")

    yield
    log_info("FastAPI shutting down...")
    concurrency_manager.shutdown()
    run_shutdown_tasks()


_STATUS_MAP: dict[type, int] = {
    AuthenticationError: 401,
    AuthorizationError: 403,
    NotFoundError:      404,
    DuplicateError:     409,
    ValidationError:    422,
    RateLimitError:     429,
    WorkflowError:      500,
    ExternalServiceError: 502,
    OAuthError:         401,
}


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AI Study Roadmap API",
        description="REST API for AI-powered study assistant with multi-agent workflows",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ── Middleware (order matters: last added = first executed) ─────────

    # 1. CORS — config-driven
    cors = get_cors_config()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors.allowed_origins,
        allow_credentials=cors.allow_credentials,
        allow_methods=cors.allowed_methods,
        allow_headers=cors.allowed_headers,
        max_age=cors.max_age,
    )

    # 2. Request ID + timing middleware
    from core.middleware import RequestIdMiddleware, SecurityHeadersMiddleware
    app.add_middleware(RequestIdMiddleware)

    # 3. Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Convert AppException subclasses → structured JSON error responses."""
        status_code = _STATUS_MAP.get(type(exc), 500)
        request_id = getattr(request.state, "request_id", None)
        log_warning(f"AppException [{exc.error_code}]: {exc.message} (req={request_id})")
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details or None,
                    "request_id": request_id,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Pydantic / FastAPI validation errors → friendly 422 with field details."""
        request_id = getattr(request.state, "request_id", None)
        # Simplify error details for the client
        field_errors = []
        for err in exc.errors():
            loc = " → ".join(str(l) for l in err.get("loc", []))
            field_errors.append({
                "field": loc,
                "message": err.get("msg", "Invalid value"),
                "type": err.get("type", "value_error"),
            })
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": {"fields": field_errors},
                    "request_id": request_id,
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch-all for unhandled exceptions → safe 500 response.

        Never leaks stack traces to the client.
        """
        request_id = getattr(request.state, "request_id", None)
        log_error(f"Unhandled exception (req={request_id}): {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                },
            },
        )

    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator(
        should_group_status_codes=True,
        excluded_handlers=["/metrics", "/api/v1/health"],
    ).instrument(app).expose(app, endpoint="/metrics")

    from routers import v1_router
    app.include_router(v1_router, prefix="/api/v1")

    return app


# Module-level instance for uvicorn
app = create_app()
