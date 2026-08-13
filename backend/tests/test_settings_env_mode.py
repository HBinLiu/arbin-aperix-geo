"""Settings env file mode selection."""

from __future__ import annotations

import os
from pathlib import Path

from aperix_geo.config import resolve_settings_env_mode, settings_env_files


def test_resolve_settings_env_mode_defaults_to_development(monkeypatch) -> None:
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setattr("aperix_geo.config._mode_from_marker_file", lambda: None)
    assert resolve_settings_env_mode() == "development"


def test_resolve_settings_env_mode_production_aliases(monkeypatch) -> None:
    monkeypatch.setenv("ENV", "prod")
    assert resolve_settings_env_mode() == "production"
    monkeypatch.setenv("ENV", "production")
    assert resolve_settings_env_mode() == "production"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ENV", raising=False)
    assert resolve_settings_env_mode() == "production"


def test_resolve_settings_env_mode_explicit_beats_marker(monkeypatch) -> None:
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setattr("aperix_geo.config._mode_from_marker_file", lambda: "production")
    assert resolve_settings_env_mode() == "development"


def test_resolve_settings_env_mode_from_marker_file_sets_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    marker = tmp_path / ".env.mode"
    marker.write_text("production\n", encoding="utf-8")
    monkeypatch.setattr("aperix_geo.config._MODE_MARKER_FILE", marker)
    assert resolve_settings_env_mode() == "production"
    assert os.environ.get("ENV") == "production"


def test_settings_env_files_only_mode_file(monkeypatch) -> None:
    monkeypatch.setenv("ENV", "development")
    files = settings_env_files()
    assert len(files) == 1
    assert Path(files[0]).name == ".env.development"
    monkeypatch.setenv("ENV", "production")
    files = settings_env_files()
    assert len(files) == 1
    assert Path(files[0]).name == ".env.production"
