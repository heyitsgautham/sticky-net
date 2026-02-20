"""
Shared pytest fixtures for the simulated GUVI evaluation test suite.
"""

import os
import sys
import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup (must be FIRST so the rest can use these)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SIMULATED_DIR = Path(__file__).resolve().parent
SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"

# Ensure project root and simulated-testing dir are on sys.path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SIMULATED_DIR) not in sys.path:
    sys.path.insert(0, str(SIMULATED_DIR))

# ---------------------------------------------------------------------------
# Environment variables — must be set BEFORE importing src modules
# ---------------------------------------------------------------------------
# Load from .env file if it exists
_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _, _val = _line.partition("=")
                os.environ.setdefault(_key.strip(), _val.strip())

os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "sticky-net-485205")
os.environ.setdefault("GUVI_CALLBACK_ENABLED", "false")
os.environ.setdefault("DEBUG", "true")

from starlette.testclient import TestClient

from src.main import create_app
from scenario_runner import ScenarioRunner, load_scenario
from guvi_scoring_engine import ScoreBreakdown


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def app():
    """Create the FastAPI application."""
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    """FastAPI TestClient for the simulated-testing session."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def api_key() -> str:
    return os.environ.get("API_KEY", "test-api-key-simulated")


@pytest.fixture(scope="session")
def auth_headers(api_key) -> dict:
    return {
        "Content-Type": "application/json",
        "x-api-key": api_key,
    }


@pytest.fixture(scope="session")
def runner(client, auth_headers) -> ScenarioRunner:
    """ScenarioRunner instance for the entire test session."""
    return ScenarioRunner(client, auth_headers)


@pytest.fixture
def scenarios_dir() -> Path:
    """Path to the scenarios directory."""
    return SCENARIOS_DIR


# ---------------------------------------------------------------------------
# Helpers for loading scenarios
# ---------------------------------------------------------------------------
def get_scenario_files(category: str) -> list[Path]:
    """Get all JSON scenario files for a category."""
    category_dir = SCENARIOS_DIR / category
    if not category_dir.exists():
        return []
    return sorted(category_dir.glob("*.json"))


def load_scenario_ids(category: str) -> list[str]:
    """Get scenario IDs for parametrize."""
    files = get_scenario_files(category)
    ids = []
    for f in files:
        with open(f) as fp:
            data = json.load(fp)
            ids.append(data.get("scenarioId", f.stem))
    return ids


def scenario_params(category: str):
    """Generate pytest.param objects for all scenarios in a category."""
    files = get_scenario_files(category)
    params = []
    for f in files:
        with open(f) as fp:
            data = json.load(fp)
        sid = data.get("scenarioId", f.stem)
        params.append(pytest.param(data, id=sid))
    return params
