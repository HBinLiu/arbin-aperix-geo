"""Shared API pagination helpers."""

from __future__ import annotations

from aperix_geo.services.billing.constants import API_PAGE_SIZE_MAX


def normalize_pagination(page: int, page_size: int, *, max_page_size: int = API_PAGE_SIZE_MAX) -> tuple[int, int]:
    safe_max = max(1, max_page_size)
    return max(1, page), max(1, min(page_size, safe_max))
