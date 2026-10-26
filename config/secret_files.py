"""Load secret settings from files as well as from environment variables.

Cloud Run can mount a Secret Manager secret as a file, and Docker and Kubernetes
secrets arrive the same way. Setting ``API_KEY_FILE=/secrets/api-key`` makes
Settings read ``api_key`` from that file, so the key never sits in the process
environment, where ``/proc/<pid>/environ`` and crash dumps can expose it.

A plain ``API_KEY`` environment variable still wins when both are set, so existing
``--set-secrets=API_KEY=...`` deployments behave exactly as before.
"""

import os
from pathlib import Path
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource

# Settings fields that hold credentials and may be supplied through <FIELD>_FILE.
SECRET_FIELDS: tuple[str, ...] = ("api_key",)


class SecretFileError(ValueError):
    """A <FIELD>_FILE variable points at a file that cannot supply the secret."""


def file_variable(field_name: str) -> str:
    """Name of the environment variable that holds the path for ``field_name``."""
    return f"{field_name.upper()}_FILE"


def read_secret_file(path: str, variable: str) -> str:
    """Return the secret stored at ``path``, without its trailing newline.

    Error messages name the variable and path, never the file's contents.
    """
    try:
        value = Path(path).read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise SecretFileError(f"{variable} points at {path}, which cannot be read") from exc
    if not value:
        raise SecretFileError(f"{variable} points at {path}, which is empty")
    return value


def _lookup(environ: dict[str, str], name: str) -> str | None:
    """Case-insensitive environment lookup, matching Settings(case_sensitive=False)."""
    wanted = name.lower()
    for key, value in environ.items():
        if key.lower() == wanted:
            return value
    return None


class FileSecretsSource(PydanticBaseSettingsSource):
    """Settings source that reads each of SECRET_FIELDS from its <FIELD>_FILE path."""

    def __init__(
        self, settings_cls: type[BaseSettings], environ: dict[str, str] | None = None
    ) -> None:
        super().__init__(settings_cls)
        self._environ = dict(os.environ) if environ is None else environ

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        path = _lookup(self._environ, file_variable(field_name))
        if not path:
            return None, field_name, False
        return read_secret_file(path, file_variable(field_name)), field_name, False

    def __call__(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for field_name in SECRET_FIELDS:
            field = self.settings_cls.model_fields.get(field_name)
            if field is None:
                continue
            value, _, _ = self.get_field_value(field, field_name)
            if value is not None:
                values[field_name] = value
        return values
