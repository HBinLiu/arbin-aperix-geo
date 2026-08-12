"""Doubao Web sampling via Playwright (crawl-first path)."""

from aperix_geo.services.providers.doubao_web.crawler import crawl_doubao_chat, user_prompt_from_messages
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
