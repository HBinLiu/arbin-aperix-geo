"""Logging configuration tests."""

import logging

from aperix_geo.utils.logging import configure_third_party_loggers


def test_configure_third_party_loggers_sets_httpx_warning() -> None:
    configure_third_party_loggers()
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
