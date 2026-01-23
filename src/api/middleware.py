"""API middleware for authentication and request processing."""

import time
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import get_settings


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API key in request headers."""

    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate API key for protected endpoints."""
        # Skip auth for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Get API key from header
        api_key = request.headers.get("x-api-key")
        settings = get_settings()

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"status": "error", "error": "Missing API key"},
            )

        if api_key != settings.api_key:
            return JSONResponse(
                status_code=403,
                content={"status": "error", "error": "Invalid API key"},
            )

        return await call_next(request)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Middleware to track request timing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add timing information to response headers."""
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        return response


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application."""
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(APIKeyMiddleware)