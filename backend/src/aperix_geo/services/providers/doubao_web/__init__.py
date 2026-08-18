"""Doubao Web sampling via Playwright (crawl-first path).

Keep this package init import-light: geo-web-crawl image startup must not pull
SQLAlchemy via ``crawler`` → ``accounts`` → ``pool``.
"""

from aperix_geo.services.providers.doubao_web.errors import (
    DoubaoCaptchaRequired,
    DoubaoCrawlError,
    DoubaoLoginExpired,
    DoubaoNeedsHumanOps,
    DoubaoShareError,
)

__all__ = [
    "DoubaoCaptchaRequired",
    "DoubaoCrawlError",
    "DoubaoLoginExpired",
    "DoubaoNeedsHumanOps",
    "DoubaoShareError",
    "crawl_doubao_chat",
    "user_prompt_from_messages",
]


def __getattr__(name: str):
    if name in {"crawl_doubao_chat", "user_prompt_from_messages"}:
        from aperix_geo.services.providers.doubao_web import crawler as _crawler

        return getattr(_crawler, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
