"""Helpers shared across test modules."""

from typing import Any

from config.settings import Settings


def make_settings(**overrides: Any) -> Settings:
    """Build Settings from explicit values only, never from the developer's .env."""
    values: dict[str, Any] = {
        "api_key": "prod-key-for-tests",
        "google_cloud_project": "test-project",
        "debug": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[call-arg]
