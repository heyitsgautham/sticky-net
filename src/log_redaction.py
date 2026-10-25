"""Mask credentials before a log line is rendered.

The processor runs for structlog and stdlib records alike, so a header dict, a
settings dump or an f-string that happens to carry a key never reaches stdout or
Cloud Logging in clear text.
"""

import re
from collections.abc import Mapping, MutableMapping
from typing import Any

REDACTED = "[REDACTED]"

# Field names that always hold a credential, compared lower-case with "-" as "_".
_SECRET_NAMES = frozenset(
    {
        "api_key",
        "x_api_key",
        "apikey",
        "authorization",
        "cookie",
        "set_cookie",
        "password",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "client_secret",
        "private_key",
    }
)
_SECRET_SUFFIXES = ("_api_key", "_secret", "_password", "_token", "_private_key")

# Credentials written inline in a message, such as "x-api-key: abc" or "Bearer abc".
_INLINE_PATTERNS = (
    re.compile(r"(?i)(x-api-key[\"']?\s*[:=]\s*[\"']?)[^\s\"',}]+"),
    re.compile(r"(?i)(\bbearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(\bapi[_-]?key[\"']?\s*[:=]\s*[\"']?)[^\s\"',}&]+"),
)


def is_secret_name(name: str) -> bool:
    """True when a field called ``name`` should never be logged in clear."""
    normalised = name.lower().replace("-", "_")
    return normalised in _SECRET_NAMES or normalised.endswith(_SECRET_SUFFIXES)


def redact_text(text: str) -> str:
    """Mask inline credentials in free text, leaving the label visible."""
    for pattern in _INLINE_PATTERNS:
        text = pattern.sub(lambda m: m.group(1) + REDACTED, text)
    return text


def redact_value(value: Any) -> Any:
    """Redact ``value`` recursively: mappings by key name, strings by pattern."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {
            key: REDACTED if isinstance(key, str) and is_secret_name(key) else redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return type(value)(redact_value(item) for item in value)
    return value


def redact_secrets(
    _logger: object, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """structlog processor that masks credentials in every field of a record."""
    for key, value in list(event_dict.items()):
        if key.startswith("_"):
            continue  # structlog's own bookkeeping, such as _record and _from_structlog
        event_dict[key] = REDACTED if is_secret_name(key) else redact_value(value)
    return event_dict
