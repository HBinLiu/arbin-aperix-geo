"""Doubao platform handler — dispatches by normalized job mode."""

from __future__ import annotations

from typing import Any

from aperix_geo.services.crawl_browser.registry import register_platform
from aperix_geo.services.providers.doubao_web.runtime import normalize_doubao_job_mode


def handle_doubao(payload: dict[str, Any], page: Any, context: Any) -> dict[str, Any]:
    mode = normalize_doubao_job_mode(str(payload.get("mode") or ""))

    if mode == "probe":
        from aperix_geo.services.providers.doubao_web.jobs.probe import (
            run_doubao_login_probe_on_page,
        )

        return run_doubao_login_probe_on_page(page, context, payload)
    if mode == "sign":
        from aperix_geo.services.providers.doubao_web.jobs.sign import (
            run_doubao_sign_on_page,
        )

        return run_doubao_sign_on_page(page, context, payload)
    if mode == "http":
        from aperix_geo.services.providers.doubao_web.jobs.http import (
            run_doubao_web_http_on_page,
        )

        return run_doubao_web_http_on_page(page, context, payload)
    if mode == "share":
        from aperix_geo.services.providers.doubao_web.jobs.share import (
            run_doubao_share_on_page,
        )

        return run_doubao_share_on_page(page, context, payload)

    from aperix_geo.services.providers.doubao_web.jobs.crawl import (
        run_doubao_browser_crawl_on_page,
    )

    return run_doubao_browser_crawl_on_page(page, context, payload)


register_platform("doubao", handle_doubao)
