"""Doubao Web crawl errors (Playwright path)."""

from __future__ import annotations


class DoubaoCrawlError(Exception):
    """Generic Doubao web crawl failure (DOM / timeout / empty reply)."""


class DoubaoLoginExpired(DoubaoCrawlError):
    """storage_state invalid or page requires login."""


class DoubaoShareError(DoubaoCrawlError):
    """Share button / clipboard / share URL unavailable."""
