"""API_KEY_FILE, read by config.secret_files."""

from pathlib import Path

import pytest
from pydantic_settings import BaseSettings

from config.secret_files import (
    FileSecretsSource,
    SecretFileError,
    file_variable,
    read_secret_file,
)
from config.settings import Settings


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Drop the suite-wide API_KEY so each test decides where the key comes from."""
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    return monkeypatch


def _secret(tmp_path: Path, name: str, content: str) -> str:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_api_key_comes_from_the_file(tmp_path: Path, clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("API_KEY_FILE", _secret(tmp_path, "api-key", "from-file\n"))
    assert Settings(_env_file=None).api_key == "from-file"  # type: ignore[call-arg]


def test_lowercase_variable_name_works(tmp_path: Path, clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("api_key_file", _secret(tmp_path, "api-key", "lower"))
    assert Settings(_env_file=None).api_key == "lower"  # type: ignore[call-arg]


def test_environment_variable_wins_over_the_file(
    tmp_path: Path, clean_env: pytest.MonkeyPatch
) -> None:
    clean_env.setenv("API_KEY", "env-key")
    clean_env.setenv("API_KEY_FILE", _secret(tmp_path, "api-key", "file-key"))
    assert Settings(_env_file=None).api_key == "env-key"  # type: ignore[call-arg]


def test_file_wins_over_dotenv(tmp_path: Path, clean_env: pytest.MonkeyPatch) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("API_KEY=dotenv-key\n", encoding="utf-8")
    clean_env.setenv("API_KEY_FILE", _secret(tmp_path, "api-key", "file-key"))
    assert Settings(_env_file=str(dotenv)).api_key == "file-key"  # type: ignore[call-arg]


def test_missing_file_fails_without_leaking(tmp_path: Path, clean_env: pytest.MonkeyPatch) -> None:
    missing = tmp_path / "nope"
    clean_env.setenv("API_KEY_FILE", str(missing))
    with pytest.raises(
        SecretFileError, match="API_KEY_FILE points at .*nope, which cannot be read"
    ):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_empty_file_fails(tmp_path: Path, clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("API_KEY_FILE", _secret(tmp_path, "api-key", "  \n"))
    with pytest.raises(SecretFileError, match="which is empty"):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_unreadable_path_is_a_secret_file_error(tmp_path: Path) -> None:
    # A directory is a common mistake when a secret volume is mounted at the wrong level.
    with pytest.raises(SecretFileError, match="cannot be read"):
        read_secret_file(str(tmp_path), "API_KEY_FILE")


def test_source_only_reads_secret_fields(tmp_path: Path) -> None:
    environ = {
        "API_KEY_FILE": _secret(tmp_path, "a", "a-key"),
        "DEBUG_FILE": _secret(tmp_path, "d", "true"),
    }
    values = FileSecretsSource(Settings, environ=environ)()
    assert values == {"api_key": "a-key"}


def test_source_skips_fields_the_settings_class_lacks(tmp_path: Path) -> None:
    class Minimal(BaseSettings):
        port: int = 8080

    environ = {"API_KEY_FILE": _secret(tmp_path, "a", "unused")}
    assert FileSecretsSource(Minimal, environ=environ)() == {}


def test_file_variable_name() -> None:
    assert file_variable("api_key") == "API_KEY_FILE"
