"""Configure application loggers (stderr + optional rotating file)."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path

_STREAM_HANDLER_NAME = "aperix_geo.stream"
_FILE_HANDLER_NAME = "aperix_geo.file"

_STREAM_FORMAT = "%(levelname)s:     %(message)s"
_FILE_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
_FILE_DATEFMT = "%Y-%m-%d %H:%M:%S"


def _truthy(raw: str | None, *, default: bool = False) -> bool:
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _parse_bytes(raw: str, *, default: int) -> int:
    text = (raw or "").strip().lower().replace("_", "")
    if not text:
        return default
    mult = 1
    if text.endswith("kb"):
        mult = 1024
        text = text[:-2]
    elif text.endswith("mb"):
        mult = 1024 * 1024
        text = text[:-2]
    elif text.endswith("gb"):
        mult = 1024 * 1024 * 1024
        text = text[:-2]
    elif text.endswith("b"):
        text = text[:-1]
    try:
        return max(1024, int(float(text) * mult))
    except ValueError:
        return default


def configure_third_party_loggers() -> None:
    """Silence noisy HTTP client INFO logs (httpx logs every request at INFO)."""
    level_name = os.environ.get("HTTPX_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)
    for name in ("httpx", "httpcore", "hpack"):
        logging.getLogger(name).setLevel(level)


def _ensure_stream_handler(app_logger: logging.Logger, *, log_level: int) -> None:
    for handler in app_logger.handlers:
        if handler.get_name() == _STREAM_HANDLER_NAME:
            handler.setLevel(log_level)
            return
    handler = logging.StreamHandler(sys.stderr)
    handler.set_name(_STREAM_HANDLER_NAME)
    handler.setLevel(log_level)
    handler.setFormatter(logging.Formatter(_STREAM_FORMAT))
    app_logger.addHandler(handler)


def _resolve_log_path() -> Path | None:
    """Return log file path when ``LOG_TO_FILE`` is enabled; else None."""
    if not _truthy(os.environ.get("LOG_TO_FILE"), default=False):
        return None
    explicit = (os.environ.get("LOG_FILE") or "").strip()
    if explicit:
        path = Path(explicit).expanduser()
    else:
        log_dir = Path((os.environ.get("LOG_DIR") or "logs").strip() or "logs").expanduser()
        name = (os.environ.get("LOG_FILENAME") or "aperix.log").strip() or "aperix.log"
        path = log_dir / name
    if _truthy(os.environ.get("LOG_FILE_PER_PROCESS"), default=False):
        path = path.with_name(f"{path.stem}.{os.getpid()}{path.suffix or '.log'}")
    return path


def _build_file_handler(path: Path, *, log_level: int) -> logging.Handler:
    path.parent.mkdir(parents=True, exist_ok=True)
    rotate = (os.environ.get("LOG_ROTATE") or "midnight").strip().lower() or "midnight"
    backup = max(1, int(os.environ.get("LOG_BACKUP_COUNT") or "14"))
    if rotate in {"size", "bytes", "rotating"}:
        max_bytes = _parse_bytes(os.environ.get("LOG_MAX_BYTES") or "", default=50 * 1024 * 1024)
        handler: logging.Handler = RotatingFileHandler(
            path,
            maxBytes=max_bytes,
            backupCount=backup,
            encoding="utf-8",
            delay=True,
        )
    else:
        # midnight | daily | time (TimedRotatingFileHandler when=)
        when = "midnight" if rotate in {"midnight", "daily", "day", "time"} else rotate
        handler = TimedRotatingFileHandler(
            path,
            when=when,
            interval=1,
            backupCount=backup,
            encoding="utf-8",
            delay=True,
            utc=False,
        )
    handler.set_name(_FILE_HANDLER_NAME)
    handler.setLevel(log_level)
    handler.setFormatter(logging.Formatter(_FILE_FORMAT, datefmt=_FILE_DATEFMT))
    return handler


def _ensure_file_handler(app_logger: logging.Logger, *, log_level: int) -> Path | None:
    path = _resolve_log_path()
    existing = [h for h in app_logger.handlers if h.get_name() == _FILE_HANDLER_NAME]
    if path is None:
        for handler in existing:
            app_logger.removeHandler(handler)
            handler.close()
        return None

    target = str(path.resolve())
    for handler in existing:
        base = getattr(handler, "baseFilename", None)
        if base and str(Path(base).resolve()) == target:
            handler.setLevel(log_level)
            return path
        app_logger.removeHandler(handler)
        handler.close()

    app_logger.addHandler(_build_file_handler(path, log_level=log_level))
    return path


def configure(level: str | None = None) -> None:
    """Attach stderr (+ optional rotating file) handlers to ``aperix_geo``.

    Uvicorn only configures its own loggers; without this, ``logger.info`` in
    services is dropped (only WARNING+ may reach lastResort).

    File logging (optional, off by default)::

        LOG_TO_FILE=1
        LOG_DIR=logs                 # or LOG_FILE=/var/log/aperix/api.log
        LOG_ROTATE=midnight          # or size
        LOG_BACKUP_COUNT=14
        LOG_MAX_BYTES=50MB           # when LOG_ROTATE=size
        LOG_FILE_PER_PROCESS=1       # Celery multi-worker: aperix.<pid>.log
    """
    level_name = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, level_name, logging.INFO)

    app_logger = logging.getLogger("aperix_geo")
    app_logger.setLevel(log_level)

    _ensure_stream_handler(app_logger, log_level=log_level)
    log_path = _ensure_file_handler(app_logger, log_level=log_level)

    app_logger.propagate = False
    configure_third_party_loggers()

    if log_path is not None and not getattr(configure, "_file_announced", False):
        configure._file_announced = True  # type: ignore[attr-defined]
        app_logger.info("file logging enabled path=%s", log_path)
