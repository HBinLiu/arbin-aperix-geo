"""Login ticket URL helpers (noVNC link + complete-by-token callback)."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def advertised_vnc_port(raw: Any) -> int:
    """Port crawl reports for ``GEO_CRAWL_OPS_NOVNC_BASE_URL`` ``{port}``."""
    try:
        port = int(raw)
    except (TypeError, ValueError):
        return 0
    return port if 1 <= port <= 65535 else 0


def build_login_url(base_url: str, *, ticket_token: str, host_port: int = 0) -> str:
    """Support templates ``{ticket}`` / ``{port}``; default ``{base}/?ticket=…``.

    ``host_port`` is the crawl instance's advertised public noVNC port (not a
    repo-wide constant). Omit ``{port}`` for a single fixed reverse-proxy path.
    """
    base = (base_url or "").strip().rstrip("/")
    if not base:
        return ""
    if "{ticket}" in base or "{port}" in base:
        return base.format(ticket=ticket_token, port=host_port or "")
    return f"{base}/?ticket={ticket_token}"


def build_novnc_desktop_url(base_url: str, *, host_port: int) -> str:
    """noVNC URL for the shared crawl desktop (same template as ticket ``login_url``)."""
    return build_login_url(base_url, ticket_token="", host_port=host_port)


def build_complete_callback_url(callback_base_url: str) -> str:
    """Map API base (or full path) to complete-by-token endpoint."""
    base = (callback_base_url or "").strip().rstrip("/")
    if not base:
        return ""
    if base.endswith("/tickets/complete-by-token"):
        return base
    return f"{base}/api/v1/ops/geo-crawl/tickets/complete-by-token"


def rewrite_loopback_callback_url(complete_url: str) -> str:
    """Rewrite 127.0.0.1/localhost so geo-web-crawl can POST complete-by-token."""
    url = (complete_url or "").strip()
    if not url:
        return ""
    rewritten = re.sub(
        r"^(https?://)(?:127\.0\.0\.1|localhost)(?=[:/]|$)",
        r"\1host.docker.internal",
        url,
        count=1,
        flags=re.IGNORECASE,
    )
    if rewritten != url:
        logger.warning(
            "geo-web-crawl callback rewritten: %s → %s "
            "(set GEO_CRAWL_OPS_CALLBACK_BASE_URL to a container-reachable host)",
            url,
            rewritten,
        )
    return rewritten
