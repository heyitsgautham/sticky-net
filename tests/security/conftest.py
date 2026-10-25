"""Shared helpers for the security suite."""

from collections.abc import Callable, Iterator
from typing import Any
from unittest.mock import patch

import pytest

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


@pytest.fixture
def use_settings() -> Iterator[Callable[..., Settings]]:
    """Patch the settings the API key middleware reads, per test."""
    patcher = patch("src.api.middleware.get_settings")
    mocked = patcher.start()

    def apply(**overrides: Any) -> Settings:
        settings = make_settings(**overrides)
        mocked.return_value = settings
        return settings

    apply()
    yield apply
    patcher.stop()
