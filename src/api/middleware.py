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

    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/", "/static", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
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
            if api_key and api_key != settings.api_key:
                return JSONResponse(
                    status_code=403,
                    content={"status": "error", "error": "Invalid API key"},
                )
            # If no API key, allow through in debug mode
            return await call_next(request)

        # Production mode: require API key
        api_key = request.headers.get("x-api-key")

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"status": "error", "error": "Missing API key"},
            )

        # Accept both production key and hackathon test key
        valid_keys = {settings.api_key, "test-api-key"}
        if api_key not in valid_keys:
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