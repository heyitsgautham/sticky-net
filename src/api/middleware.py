"""API middleware for authentication and request processing."""

import time

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from config.settings import get_settings
from src.api.auth import accepted_api_keys, key_matches
from src.metrics import AUTH_FAILURES, HTTP_LATENCY, HTTP_REQUESTS, UNROUTED

logger = structlog.get_logger()


def _reject(request: Request, status_code: int, reason: str, message: str) -> JSONResponse:
    """Count and log an auth rejection, then build its reply. The key is never logged."""
    AUTH_FAILURES.labels(reason=reason).inc()
    logger.warning(
        "API key rejected",
        security_event="auth_failure",
        reason=reason,
        path=request.url.path,
        client=request.client.host if request.client else None,
    )
    return JSONResponse(status_code=status_code, content={"status": "error", "error": message})


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API key in request headers."""

    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/", "/static", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Validate API key for protected endpoints."""
        # Allow CORS preflight requests through without authentication
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip auth for exempt paths
        if request.url.path in self.EXEMPT_PATHS or request.url.path.startswith("/static"):
            return await call_next(request)

        settings = get_settings()

        # In debug mode, allow requests without API key for easier development/testing
        if settings.debug:
            api_key = request.headers.get("x-api-key")
            # If API key is provided, validate it
            if api_key and not key_matches(api_key, [settings.api_key]):
                return _reject(request, 403, "invalid", "Invalid API key")
            # If no API key, allow through in debug mode
            return await call_next(request)

        # Production mode: require API key
        api_key = request.headers.get("x-api-key")

        if not api_key:
            return _reject(request, 401, "missing", "Missing API key")

        # Accept the production key and the GUVI evaluator's shared key.
        if not key_matches(api_key, accepted_api_keys(settings)):
            return _reject(request, 403, "invalid", "Invalid API key")

        return await call_next(request)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware to track request timing."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Add timing information to response headers."""
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        return response


def _route_label(request: Request) -> str:
    """Route template the router matched, or UNROUTED for requests it never handled."""
    path = getattr(request.scope.get("route"), "path", None)
    return path if isinstance(path, str) and path else UNROUTED


class MetricsMiddleware(BaseHTTPMiddleware):
    """Count every request and time it, labelled by route template.

    It is the outermost middleware, so auth rejections are counted too. Routed
    requests are labelled by template (``/api/v1/analyze``). Requests the router never
    handled, a 404 or a 401 from APIKeyMiddleware, share one ``unrouted`` label, so
    probing random URLs cannot add new series.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Record the status and duration of one request."""
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            label = _route_label(request)
            HTTP_REQUESTS.labels(method=request.method, route=label, status=str(status)).inc()
            HTTP_LATENCY.labels(route=label).observe(time.perf_counter() - start)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add browser hardening headers to every response.

    JSON routes also get ``Cache-Control: no-store``, because replies carry extracted
    bank and UPI details, and a CSP that forbids loading anything. The static tester
    page at ``/`` uses inline handlers, so it gets the base headers only.
    """

    BASE_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
    }
    API_HEADERS = {
        "Cache-Control": "no-store",
        "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    }
    API_PREFIXES = ("/api/", "/health")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Set the headers a route has not already set."""
        response = await call_next(request)
        headers = dict(self.BASE_HEADERS)
        if request.url.path.startswith(self.API_PREFIXES):
            headers.update(self.API_HEADERS)
        for name, value in headers.items():
            response.headers.setdefault(name, value)
        return response


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application.

    Starlette runs the last one added first, so MetricsMiddleware and
    SecurityHeadersMiddleware both see the 401 and 403 replies from APIKeyMiddleware.
    """
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(APIKeyMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(MetricsMiddleware)
