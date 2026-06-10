"""Tests for ParsedSamplingResult."""

from __future__ import annotations

from aperix_geo.services.sampling.parsed import ParsedSamplingResult


def test_parsed_sampling_result_roundtrip() -> None:
    original = ParsedSamplingResult(
        urls=["https://example.com"],
        url_hosts=["example.com"],
        mentions_own=True,
        mention_count_own=2,
        mentions_competitors={"beta.com": True},
        mention_counts_competitors={"beta.com": 1},
        sentiment_own="positive",
        sentiment_score_own=90.0,
        own_brand="Aperix",
        citation_urls_own=["https://aperix.com/docs"],
        has_own_domain_link=True,
        cited_own_domain=True,
    )
    restored = ParsedSamplingResult.from_dict(original.to_dict())
    assert restored.mentions_own is True
    assert restored.mention_count_own == 2
    assert restored.sentiment_score_own == 90.0
    assert restored.citation_urls_own == ["https://aperix.com/docs"]
    assert restored.own_brand == "Aperix"
