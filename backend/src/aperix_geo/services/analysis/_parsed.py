"""Helpers for reading parsed LLM response fields."""

from __future__ import annotations

from typing import Any

from aperix_geo.utils.coerce import safe_float, safe_int
from aperix_geo.utils.sentiment import sentiment_points


def mentions_own(parsed: dict[str, Any]) -> bool:
    if parsed.get("mentions_own"):
        return True
    return safe_int(parsed, "mention_count_own") > 0


def has_own_domain_link(parsed: dict[str, Any]) -> bool:
    if "has_own_domain_link" in parsed:
        return bool(parsed.get("has_own_domain_link"))
    urls = parsed.get("citation_urls_own") or []
    return bool(urls)


def cited_competitor_on_source(parsed: dict[str, Any], label: str) -> bool:
    cited = parsed.get("cited_competitors_on_source")
    if isinstance(cited, dict) and label in cited:
        return bool(cited.get(label))
    hosts = parsed.get("url_hosts") or []
    host_str = " ".join(str(h) for h in hosts) if isinstance(hosts, list) else ""
    return label in host_str


def parsed_sentiment_score(parsed: dict[str, Any], key: str = "sentiment_score_own") -> float | None:
    return sentiment_points(safe_float(parsed, key))


def avg_sentiment_points(scores: list[float]) -> float | None:
    if not scores:
        return None
    return round(sum(scores) / len(scores), 1)


def competitors_mentioned(parsed: dict[str, Any], *, labels: list[str], own: str) -> list[str]:
    mc = parsed.get("mentions_competitors") or {}
    if not isinstance(mc, dict):
        return []
    return [lab for lab in labels if lab != own and mc.get(lab)]


def reply_text(raw_text: str) -> str:
    return (raw_text or "").replace("\n", " ").strip()
