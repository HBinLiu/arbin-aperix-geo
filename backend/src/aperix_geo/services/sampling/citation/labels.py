"""Read helpers for brand mention lists from citation LLM analysis."""

from __future__ import annotations

from typing import Any


def page_mentioned_brand_names(analysis: dict[str, Any] | None) -> list[str]:
    """Brand names mentioned on the citation source page (from page GEO analysis)."""
    if not isinstance(analysis, dict):
        return []
    brands = analysis.get("page_mentioned_brands")
    if isinstance(brands, list):
        return [str(name).strip() for name in brands if str(name).strip()]
    return []


def ai_mentioned_brand_names(response_absa: dict[str, Any] | None) -> list[str]:
    """Brand names mentioned in the sampling AI response (from response ABSA)."""
    if not isinstance(response_absa, dict):
        return []
    brands = response_absa.get("brands_sentiment_absa")
    if not isinstance(brands, dict):
        return []
    names: list[str] = []
    for name, entry in brands.items():
        label = str(name or "").strip()
        if label and isinstance(entry, dict) and entry.get("mentioned"):
            names.append(label)
    return names


def brand_names_match(names: list[str], mentioned: list[str]) -> bool:
    """Case-insensitive match between configured brand keys and mentioned list."""
    if not names or not mentioned:
        return False
    mentioned_keys = {m.strip().lower() for m in mentioned if m.strip()}
    return any(n.strip().lower() in mentioned_keys for n in names if n.strip())
