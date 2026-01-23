"""API module for Sticky-Net."""

from src.api.schemas import AnalyzeRequest, AnalyzeResponse
from src.api.middleware import setup_middleware


def get_router():
    """Lazy import router to avoid circular imports."""
    from src.api.routes import router
    return router


__all__ = ["get_router", "AnalyzeRequest", "AnalyzeResponse", "setup_middleware"]
