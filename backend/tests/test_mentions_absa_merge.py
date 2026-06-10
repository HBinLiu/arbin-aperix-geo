"""Tests for ABSA-aligned mention flags and competitor alias keys."""

from __future__ import annotations

import uuid

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.sampling.mentions import (
    CompetitorEntry,
    absa_competitor_keys,
    merge_absa_mention_flags,
    parse_mentions_and_rank,
)


def _subject(*, competitors: list[Competitor] | None = None) -> Subject:
    subject_id = uuid.uuid4()
    subject = Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        aliases=["艾佩克斯"],
        website_url="https://aperix.com",
        domain="aperix.com",
    )
    if competitors is not None:
        subject.competitors = competitors
    return subject


def test_absa_competitor_keys_includes_aliases() -> None:
    entry = CompetitorEntry(
        label="beta.com",
        brand="Beta",
        terms=("Beta", "beta.com", "贝塔"),
        domain="beta.com",
        aliases=("贝塔",),
    )
    names, keys = absa_competitor_keys([entry])
    assert "Beta" in names
    assert "贝塔" in names
    assert ("贝塔", "beta.com") in keys


def test_merge_absa_overrides_rule_when_absa_says_mentioned() -> None:
    stats = {
        "mentions_own": False,
        "mention_count_own": 0,
        "mentions_competitors": {"beta.com": False},
        "mention_counts_competitors": {"beta.com": 0},
    }
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "Aperix": {"mentioned": True, "score": 0.8},
            "Beta": {"mentioned": True, "score": 0.5},
        },
    }
    merged = merge_absa_mention_flags(
        stats,
        response_absa,
        own_brand="Aperix",
        competitor_absa_keys=[("Beta", "beta.com")],
    )
    assert merged["mentions_own"] is True
    assert merged["mention_count_own"] == 1
    assert merged["mentions_competitors"]["beta.com"] is True
    assert merged["mention_counts_competitors"]["beta.com"] == 1


def test_merge_absa_clears_rule_mention_when_absa_denies() -> None:
    stats = {
        "mentions_own": True,
        "mention_count_own": 3,
        "mentions_competitors": {"beta.com": True},
        "mention_counts_competitors": {"beta.com": 2},
    }
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "Aperix": {"mentioned": False},
            "Beta": {"mentioned": False},
        },
    }
    merged = merge_absa_mention_flags(
        stats,
        response_absa,
        own_brand="Aperix",
        competitor_absa_keys=[("Beta", "beta.com")],
    )
    assert merged["mentions_own"] is False
    assert merged["mention_count_own"] == 0
    assert merged["mentions_competitors"]["beta.com"] is False
    assert merged["mention_counts_competitors"]["beta.com"] == 0


def test_competitor_alias_in_rule_matching() -> None:
    subject = _subject(competitors=[])
    subject_id = subject.id
    subject.competitors = [
        Competitor(
            id=uuid.uuid4(),
            subject_id=subject_id,
            brand="Beta",
            domain="beta.com",
            aliases=["贝塔科技"],
        ),
    ]
    stats = parse_mentions_and_rank("推荐贝塔科技的产品", subject=subject, url_hosts=[])
    assert stats["mentions_competitors"].get("beta.com") is True


def test_merge_absa_preserves_host_only_competitor_mention() -> None:
    entry = CompetitorEntry(
        label="beta.com",
        brand="Beta",
        terms=("Beta", "beta.com"),
        domain="beta.com",
    )
    stats = {
        "mentions_own": False,
        "mention_count_own": 0,
        "mentions_competitors": {"beta.com": True},
        "mention_counts_competitors": {"beta.com": 0},
    }
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "Beta": {"mentioned": False},
        },
    }
    merged = merge_absa_mention_flags(
        stats,
        response_absa,
        own_brand="Aperix",
        competitor_absa_keys=[("Beta", "beta.com")],
        url_hosts=["beta.com"],
        competitors=[entry],
    )
    assert merged["mentions_competitors"]["beta.com"] is True
