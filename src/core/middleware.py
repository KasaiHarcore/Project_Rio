"""HTTP middleware: request ID injection, timing, and security headers.

Implemented as pure ASGI middleware for minimal per-request overhead
(avoids the extra task wrapping of Starlette's BaseHTTPMiddleware).
"""

from __future__ import annotations

import time
from uuid import uuid4

from starlette.types import ASGIApp, Receive, Scope, Send


_SECURITY_HEADERS: list[tuple[bytes, bytes]] = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
]


class SecurityHeadersMiddleware:
    """Add standard security headers to every HTTP response (pure ASGI)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(_SECURITY_HEADERS)
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


class RequestIdMiddleware:
    """Inject a unique request ID and measure processing time (pure ASGI).

    The request ID is read from the incoming X-Request-Id header or
    auto-generated as a short UUID hex.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Resolve request ID from incoming headers
        request_id: str | None = None
        for key, value in scope.get("headers", []):
            if key == b"x-request-id":
                request_id = value.decode("latin-1")
                break
        if not request_id:
            request_id = uuid4().hex[:12]

        # Store on scope so downstream code can access it
        scope.setdefault("state", {})["request_id"] = request_id

        start = time.perf_counter()

        async def send_with_timing(message):
            if message["type"] == "http.response.start":
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                headers.append((b"x-process-time-ms", str(elapsed_ms).encode("latin-1")))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_timing)
