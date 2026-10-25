"""Logging setup shared by structlog and the standard library.

structlog loggers and plain ``logging`` loggers (session store, callback, uvicorn)
go through one stdout handler, so every line has the same shape: JSON objects in
production, or coloured key=value lines for local development.
"""

import logging
import sys
from typing import Literal

import structlog
from structlog.typing import Processor

from src.log_redaction import redact_secrets

LogFormat = Literal["json", "console"]

# Processors applied to every record, whether it came from structlog or stdlib logging.
_SHARED_PROCESSORS: list[Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.UnicodeDecoder(),
    # Last, so it also sees messages PositionalArgumentsFormatter has filled in.
    redact_secrets,
]


def configure_logging(level: str = "INFO", fmt: LogFormat = "json") -> None:
    """Route structlog and stdlib logging to stdout at ``level`` in ``fmt``.

    Safe to call more than once; each call replaces the root handler.
    """
    renderer: list[Processor]
    if fmt == "json":
        renderer = [structlog.processors.format_exc_info, structlog.processors.JSONRenderer()]
    else:
        renderer = [structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())]

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *_SHARED_PROCESSORS,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_SHARED_PROCESSORS,
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, *renderer],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
