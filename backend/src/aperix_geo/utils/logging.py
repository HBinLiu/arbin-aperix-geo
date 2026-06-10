"""Configure application loggers so INFO logs appear in the uvicorn terminal."""

from __future__ import annotations

import logging
import os
import sys


def configure_third_party_loggers() -> None:
    """Silence noisy HTTP client INFO logs (httpx logs every request at INFO)."""
    level_name = os.environ.get("HTTPX_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)
    for name in ("httpx", "httpcore", "hpack"):
        logging.getLogger(name).setLevel(level)


def configure(level: str | None = None) -> None:
    """Attach a stderr handler to the ``aperix_geo`` logger tree.

    Uvicorn only configures its own loggers; without this, ``logger.info`` in
    services is dropped (only WARNING+ may reach lastResort).
    """
    level_name = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, level_name, logging.INFO)

    app_logger = logging.getLogger("aperix_geo")
    app_logger.setLevel(log_level)

    if not app_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s:     %(message)s"))
        app_logger.addHandler(handler)

    app_logger.propagate = False
    configure_third_party_loggers()
