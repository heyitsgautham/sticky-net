"""API module for Sticky-Net."""

from fastapi import APIRouter

from src.api.middleware import setup_middleware
from src.api.schemas import AnalyzeRequest, AnalyzeResponse


def get_router() -> APIRouter:
    """Lazy import router to avoid circular imports."""
    from src.api.routes import router

    return router


__all__ = ["get_router", "AnalyzeRequest", "AnalyzeResponse", "setup_middleware"]
