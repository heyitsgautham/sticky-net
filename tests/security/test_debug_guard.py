"""Settings refuses DEBUG=true in production, where it would disable auth."""

import pytest
from pydantic import ValidationError

from tests.security.conftest import make_settings


@pytest.mark.parametrize("environment", ["production", "Production", " production "])
def test_debug_in_production_fails_startup(environment: str) -> None:
    with pytest.raises(ValidationError, match="DEBUG=true is not allowed"):
        make_settings(debug=True, environment=environment)


def test_production_without_debug_is_fine() -> None:
    settings = make_settings(debug=False, environment="production")
    assert settings.is_production
    assert not settings.debug


@pytest.mark.parametrize("environment", ["development", "staging"])
def test_debug_outside_production_is_allowed(environment: str) -> None:
    assert make_settings(debug=True, environment=environment).debug
