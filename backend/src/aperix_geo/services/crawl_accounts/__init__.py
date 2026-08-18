"""Multi-platform crawl account pool.

Keep this ``__init__`` import-light: geo-web-crawl only needs
``cookies`` / ``platforms`` and must not pull Redis/Celery/email via
eager package imports.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "AccountLease",
    "PLATFORM_DEEPSEEK",
    "PLATFORM_DOUBAO",
    "PLATFORM_QIANWEN",
    "acquire_account",
    "count_fresh_active_accounts",
    "mark_need_relogin",
    "release_account",
    "request_human_intervention",
    "upsert_account_from_state",
]


def __getattr__(name: str) -> Any:
    if name in {
        "AccountLease",
        "acquire_account",
        "count_fresh_active_accounts",
        "mark_need_relogin",
        "release_account",
        "upsert_account_from_state",
    }:
        from aperix_geo.services.crawl_accounts import pool as _pool

        return getattr(_pool, name)
    if name == "request_human_intervention":
        from aperix_geo.services.crawl_accounts.human_ops import request_human_intervention

        return request_human_intervention
    if name in {"PLATFORM_DEEPSEEK", "PLATFORM_DOUBAO", "PLATFORM_QIANWEN"}:
        from aperix_geo.services.crawl_accounts import platforms as _platforms

        return getattr(_platforms, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
