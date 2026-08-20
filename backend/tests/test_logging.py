"""Logging configuration tests."""

from __future__ import annotations

import logging
from pathlib import Path

from aperix_geo.utils import logging as log_util
from aperix_geo.utils.logging import configure, configure_third_party_loggers


def test_configure_third_party_loggers_sets_httpx_warning() -> None:
    configure_third_party_loggers()
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING


def test_configure_file_logging_writes_rotating_file(tmp_path: Path, monkeypatch) -> None:
    log_file = tmp_path / "aperix.log"
    monkeypatch.setenv("LOG_TO_FILE", "1")
    monkeypatch.setenv("LOG_FILE", str(log_file))
    monkeypatch.setenv("LOG_ROTATE", "size")
    monkeypatch.setenv("LOG_MAX_BYTES", "1MB")
    monkeypatch.setenv("LOG_BACKUP_COUNT", "3")
    # Allow announce once per process in tests.
    if hasattr(configure, "_file_announced"):
        delattr(configure, "_file_announced")

    app = logging.getLogger("aperix_geo")
    app.handlers.clear()

    configure(level="INFO")
    app.info("hello-file-log")
    for handler in list(app.handlers):
        handler.flush()

    assert log_file.is_file()
    text = log_file.read_text(encoding="utf-8")
    assert "hello-file-log" in text
    assert "file logging enabled" in text


def test_configure_without_file_keeps_stderr_only(monkeypatch) -> None:
    monkeypatch.delenv("LOG_TO_FILE", raising=False)
    monkeypatch.delenv("LOG_FILE", raising=False)
    app = logging.getLogger("aperix_geo")
    app.handlers.clear()
    if hasattr(configure, "_file_announced"):
        delattr(configure, "_file_announced")

    configure(level="INFO")
    names = {h.get_name() for h in app.handlers}
    assert "aperix_geo.stream" in names
    assert "aperix_geo.file" not in names


def test_parse_bytes() -> None:
    assert log_util._parse_bytes("50MB", default=1) == 50 * 1024 * 1024
    assert log_util._parse_bytes("1024", default=1) == 1024
    assert log_util._parse_bytes("bad", default=99) == 99
