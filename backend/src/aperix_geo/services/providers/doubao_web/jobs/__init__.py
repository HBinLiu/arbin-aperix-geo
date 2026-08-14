"""Doubao geo-web-crawl job implementations (one module per mode)."""

from __future__ import annotations

from aperix_geo.services.providers.doubao_web.jobs.http import (
    build_web_http_payload,
    run_doubao_web_http_on_page,
)
from aperix_geo.services.providers.doubao_web.jobs.crawl import (
    build_crawl_payload,
    run_doubao_browser_crawl_on_page,
)
from aperix_geo.services.providers.doubao_web.jobs.probe import (
    build_probe_payload,
    run_doubao_login_probe_on_page,
)
from aperix_geo.services.providers.doubao_web.jobs.share import (
    build_share_payload,
    run_doubao_share_on_page,
)
from aperix_geo.services.providers.doubao_web.jobs.sign import (
    build_sign_payload,
    run_doubao_sign_on_page,
)

__all__ = [
    "build_crawl_payload",
    "build_probe_payload",
    "build_share_payload",
    "build_sign_payload",
    "build_web_http_payload",
    "run_doubao_browser_crawl_on_page",
    "run_doubao_login_probe_on_page",
    "run_doubao_share_on_page",
    "run_doubao_sign_on_page",
    "run_doubao_web_http_on_page",
]
