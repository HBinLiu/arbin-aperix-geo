"""Doubao Web crawl errors (Playwright path)."""

from __future__ import annotations


class DoubaoCrawlError(Exception):
    """Generic Doubao web crawl failure (DOM / timeout / empty reply)."""

    session_alive: bool = False

    def __init__(self, message: str = "", *, session_alive: bool = False) -> None:
        super().__init__(message)
        self.session_alive = session_alive


class DoubaoNeedsHumanOps(DoubaoCrawlError):
    """Account blocked until ops clears via ticket + alert (not auto-solved).

    Subclasses: login expired, behavior captcha. Same recovery: need_relogin →
    human login ticket (noVNC / upload storage_state) + ops email alert.
    """

    reason: str = "human_ops"


class DoubaoLoginExpired(DoubaoNeedsHumanOps):
    """storage_state invalid or page requires login."""

    reason = "login_expired"


class DoubaoCaptchaRequired(DoubaoNeedsHumanOps):
    """Behavior captcha / challenge — same human ticket/alert path as login expiry.

    Never auto-solve. Do not wait in the sampling browser.
    """

    reason = "captcha"


class DoubaoShareError(DoubaoCrawlError):
    """Share button / clipboard / share URL unavailable."""
