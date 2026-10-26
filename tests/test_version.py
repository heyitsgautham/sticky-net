"""One version number across the package, the API docs, error reports and the dashboard."""

import json
import tomllib
from pathlib import Path

from src import __version__
from src.main import app

ROOT = Path(__file__).resolve().parent.parent


def test_pyproject_matches_the_package() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert project["version"] == __version__


def test_openapi_reports_the_package_version() -> None:
    assert app.version == __version__


def test_dashboard_matches_the_package() -> None:
    package = json.loads((ROOT / "frontend" / "package.json").read_text())
    assert package["version"] == __version__
