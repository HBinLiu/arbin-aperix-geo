"""Doubao platform handler (crawl + probe)."""

from __future__ import annotations

from typing import Any

from aperix_geo.services.geo_web_crawl.registry import register_platform


def handle_doubao(payload: dict[str, Any], page: Any, context: Any) -> dict[str, Any]:
    mode = str(payload.get("mode") or "crawl").strip().lower() or "crawl"
    if mode == "probe":
        from aperix_geo.services.providers.doubao_web.probe_job import (
            run_doubao_login_probe_on_page,
        )

        return run_doubao_login_probe_on_page(page, context, payload)
    from aperix_geo.services.providers.doubao_web.browser_crawl_job import (
        run_doubao_browser_crawl_on_page,
    )

    return run_doubao_browser_crawl_on_page(page, context, payload)


register_platform("doubao", handle_doubao)
