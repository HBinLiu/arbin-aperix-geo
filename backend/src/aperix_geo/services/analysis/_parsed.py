"""Helpers for reading parsed LLM response fields."""

from __future__ import annotations

from typing import Any

from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from aperix_geo.utils.coerce import safe_float, safe_int
from aperix_geo.utils.sentiment import sentiment_points


def _parsed_dict(parsed: dict[str, Any] | ParsedSamplingResult) -> dict[str, Any]:
    if isinstance(parsed, ParsedSamplingResult):
        return parsed.to_dict()
    return parsed


def mentions_own(parsed: dict[str, Any] | ParsedSamplingResult) -> bool:
    data = _parsed_dict(parsed)
    if data.get("mentions_own"):
        return True
    if safe_int(data, "mention_count_own") > 0:
        return True
    own_brand = str(data.get("own_brand") or "").strip()
    if not own_brand:
        return False
    absa = data.get("citation_response_absa")
    if not isinstance(absa, dict) or absa.get("analysis_source") != "llm":
        return False
    brands = absa.get("brands_sentiment_absa")
    if not isinstance(brands, dict):
        return False
    entry = brands.get(own_brand)
    if isinstance(entry, dict) and entry.get("mentioned") is True:
        return True
    return False


def has_own_domain_link(parsed: dict[str, Any] | ParsedSamplingResult) -> bool:
    data = _parsed_dict(parsed)
    if "has_own_domain_link" in data:
        return bool(data.get("has_own_domain_link"))
    urls = data.get("citation_urls_own") or []
    return bool(urls)


def cited_competitor_on_source(parsed: dict[str, Any] | ParsedSamplingResult, label: str) -> bool:
    data = _parsed_dict(parsed)
    cited = data.get("cited_competitors_on_source")
    if isinstance(cited, dict) and label in cited:
        return bool(cited.get(label))
    hosts = data.get("url_hosts") or []
    host_str = " ".join(str(h) for h in hosts) if isinstance(hosts, list) else ""
    return label in host_str


def parsed_sentiment_score(
    parsed: dict[str, Any] | ParsedSamplingResult,
    key: str = "sentiment_score_own",
) -> float | None:
    return sentiment_points(safe_float(_parsed_dict(parsed), key))


def avg_sentiment_points(scores: list[float]) -> float | None:
    if not scores:
        return None
    return round(sum(scores) / len(scores), 1)


def competitors_mentioned(
    parsed: dict[str, Any] | ParsedSamplingResult,
    *,
    labels: list[str],
    own: str,
) -> list[str]:
    mc = _parsed_dict(parsed).get("mentions_competitors") or {}
    if not isinstance(mc, dict):
        return []
    return [lab for lab in labels if lab != own and mc.get(lab)]


def reply_text(raw_text: str) -> str:
    return (raw_text or "").replace("\n", " ").strip()
