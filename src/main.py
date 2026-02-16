"""FastAPI application entry point."""

import logging
import sys
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.api.routes import router
from src.api.middleware import setup_middleware
from config.settings import get_settings

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"

# Configure standard library logging to output to console
logging.basicConfig(
    format="%(message)s",
    stream=sys.stdout,
    level=logging.INFO,
)

# Configure structured logging with console-friendly output
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(colors=True),  # Human-readable output for dev
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown."""
    settings = get_settings()
    logger.info(
        "Starting Sticky-Net",
        debug=settings.debug,
        llm_model=settings.flash_model,
    )
    yield
    logger.info("Shutting down Sticky-Net")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Sticky-Net",
        description="AI Agentic Honey-Pot for Scam Detection & Intelligence Extraction",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Custom middleware (added first, runs after CORS)
    setup_middleware(app)

    # CORS middleware (added last, runs first to handle preflight)
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://sticky-net-frontend-140367184766.asia-south1.run.app",
        "https://hackathon.guvi.in",  # Hackathon testing framework
        "https://www.hackathon.guvi.in",  # Alternative URL
    ]
    if settings.debug:
        allowed_origins.append("*")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins if not settings.debug else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.get("/")
    async def serve_ui() -> FileResponse:
        """Serve the web UI for testing."""
        return FileResponse(STATIC_DIR / "index.html")

    # Mount static files (if directory exists)
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    return app


app = create_app()