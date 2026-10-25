"""Optional Sentry error tracking, turned on by ERROR_TRACKING_DSN.

With no DSN, every function here is a no-op and nothing leaves the process.
With a DSN, exceptions the routes catch and answer with a canned reply are still
reported, so a failing Gemini call or callback shows up as an issue instead of a
log line nobody reads.
"""

from typing import Any

import sentry_sdk
import structlog
from sentry_sdk.types import Event, Hint

from config.settings import Settings
from src import __version__
from src.log_redaction import redact_value

logger = structlog.get_logger()


def scrub_event(event: Event, _hint: Hint) -> Event:
    """Mask credentials in the request, extra and breadcrumb data before sending."""
    for key in ("request", "extra", "contexts", "breadcrumbs"):
        if key in event:
            event[key] = redact_value(event[key])
    return event


def init_error_tracking(settings: Settings, **sdk_options: Any) -> bool:
    """Start Sentry when ``settings.error_tracking_dsn`` is set. Returns whether it did.

    ``sdk_options`` go to ``sentry_sdk.init`` and let tests pass a fake transport.
    """
    if not settings.error_tracking_dsn:
        return False
    sentry_sdk.init(
        dsn=settings.error_tracking_dsn,
        environment=settings.environment,
        release=f"sticky-net@{__version__}",
        traces_sample_rate=0.0,
        # The SDK's defaults leave out cookies, auth headers and user IPs;
        # scrub_event masks anything credential-shaped that is left.
        before_send=scrub_event,
        **sdk_options,
    )
    logger.info("Error tracking enabled", environment=settings.environment)
    return True


def capture_exception(exc: BaseException, **context: Any) -> None:
    """Report ``exc`` with ``context`` as tags. Does nothing when Sentry is off."""
    if not sentry_sdk.is_initialized():
        return
    with sentry_sdk.new_scope() as scope:
        for key, value in context.items():
            if value is not None:
                scope.set_tag(key, str(value))
        scope.capture_exception(exc)
