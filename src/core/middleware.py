"""HTTP middleware: request ID injection and timing.

Adds:
- X-Request-Id header to every request/response for tracing
- X-Process-Time-Ms header showing server processing time
"""

from __future__ import annotations

import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from utils.log import log_debug


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard security headers to every response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Inject a unique request ID and measure processing time.

    The request ID is:
    1. Read from the incoming ``X-Request-Id`` header (client-provided), or
    2. Auto-generated as a short UUID hex.

    Both the request ID and processing time are set on the response headers.
    The request ID is also stored in ``request.state.request_id`` so that
    exception handlers and downstream code can include it in error payloads.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Resolve request ID
        request_id = request.headers.get("X-Request-Id") or uuid4().hex[:12]
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        # Attach headers
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Process-Time-Ms"] = str(elapsed_ms)

        log_debug(f"[{request.method}] {request.url.path} → {response.status_code} ({elapsed_ms}ms) req={request_id}")

        return response
