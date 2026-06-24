"""Tests for ABSA-aligned mention flags and competitor alias keys."""

from __future__ import annotations

import uuid

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.analysis.entity import OWN_ENTITY_ID, own_entity
from aperix_geo.services.sampling.mentions import CompetitorEntry, absa_competitor_keys, absa_own_keys
from aperix_geo.services.sampling.sentiment import apply_absa_to_drafts
from aperix_geo.services.sampling.signal_draft import (
    build_mention_entity_signals,
    compute_mention_ranks,
    draft_for_entity_label,
    own_draft,
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


def _subject_with_beta() -> Subject:
    subject = _subject()
    subject.competitors = [
        Competitor(
            id=uuid.uuid4(),
            subject_id=subject.id,
            brand="Beta",
            domain="beta.com",
        )
    ]
    return subject


def test_absa_own_keys_includes_aliases() -> None:
    names, keys = absa_own_keys(
        own_brand="Aperix",
        own_match_names=["艾佩克斯", "aperix.com"],
        entity_label="Aperix",
    )
    assert "Aperix" in names
    assert "艾佩克斯" in names
    assert ("艾佩克斯", "Aperix") in keys


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


def test_merge_absa_own_alias_key_applies_sentiment() -> None:
    subject = _subject()
    drafts, _ = build_mention_entity_signals("ignored", subject=subject, url_hosts=[])
    own = own_draft(drafts)
    own.mentioned = False
    own.mention_count = 0
    own_entity_label = own_entity(subject).label
    own_names_list, own_absa_keys = absa_own_keys(
        own_brand="Aperix",
        own_match_names=list(subject.aliases or []),
        entity_label=own_entity_label,
    )

    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "艾佩克斯": {"mentioned": True, "score": 88, "evidence": "艾佩克斯很好"},
        },
    }
    apply_absa_to_drafts(
        drafts,
        response_absa,
        own_brand="Aperix",
        own_absa_keys=own_absa_keys,
        competitor_absa_keys=[],
        text="推荐艾佩克斯",
    )

    assert own.mentioned is True
    assert own.sentiment_score == 88.0


def test_merge_absa_overrides_rule_when_absa_says_mentioned() -> None:
    subject = _subject_with_beta()
    drafts, competitors = build_mention_entity_signals("ignored", subject=subject, url_hosts=[])
    own = own_draft(drafts)
    own.mentioned = False
    own.mention_count = 0
    comp = draft_for_entity_label(drafts, "beta.com")
    assert comp is not None
    comp.mentioned = False
    comp.mention_count = 0

    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "Aperix": {"mentioned": True, "score": 90},
            "Beta": {"mentioned": True, "score": 75},
        },
    }
    apply_absa_to_drafts(
        drafts,
        response_absa,
        own_brand="Aperix",
        own_absa_keys=[("Aperix", "Aperix")],
        competitor_absa_keys=[("Beta", "beta.com")],
        competitors=competitors,
    )
    assert own.mentioned is True
    assert own.mention_count == 1
    assert comp.mentioned is True
    assert comp.mention_count == 1


def test_merge_absa_clears_rule_mention_when_absa_denies() -> None:
    subject = _subject_with_beta()
    drafts, competitors = build_mention_entity_signals("ignored", subject=subject, url_hosts=[])
    own = own_draft(drafts)
    own.mentioned = True
    own.mention_count = 3
    comp = draft_for_entity_label(drafts, "beta.com")
    assert comp is not None
    comp.mentioned = True
    comp.mention_count = 2

    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "Aperix": {"mentioned": False},
            "Beta": {"mentioned": False},
        },
    }
    apply_absa_to_drafts(
        drafts,
        response_absa,
        own_brand="Aperix",
        own_absa_keys=[("Aperix", "Aperix")],
        competitor_absa_keys=[("Beta", "beta.com")],
        competitors=competitors,
    )
    assert own.mentioned is False
    assert own.mention_count == 0
    assert comp.mentioned is False
    assert comp.mention_count == 0


def test_competitor_alias_in_rule_matching() -> None:
    subject = _subject(competitors=[])
    subject.competitors = [
        Competitor(
            id=uuid.uuid4(),
            subject_id=subject.id,
            brand="Beta",
            domain="beta.com",
            aliases=["贝塔科技"],
        ),
    ]
    drafts, _ = build_mention_entity_signals("推荐贝塔科技的产品", subject=subject, url_hosts=[])
    comp = draft_for_entity_label(drafts, "beta.com")
    assert comp is not None
    assert comp.mentioned is True


def test_merge_absa_preserves_host_only_competitor_mention() -> None:
    entry = CompetitorEntry(
        label="beta.com",
        brand="Beta",
        terms=("Beta", "beta.com"),
        domain="beta.com",
    )
    subject = _subject_with_beta()
    drafts, competitors = build_mention_entity_signals("ignored", subject=subject, url_hosts=[])
    comp = draft_for_entity_label(drafts, "beta.com")
    assert comp is not None
    comp.mentioned = True
    comp.mention_count = 0

    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "Beta": {"mentioned": False},
        },
    }
    apply_absa_to_drafts(
        drafts,
        response_absa,
        own_brand="Aperix",
        own_absa_keys=[("Aperix", "Aperix")],
        competitor_absa_keys=[("Beta", "beta.com")],
        url_hosts=["beta.com"],
        competitors=[entry],
    )
    assert comp.mentioned is True


def test_absa_only_mention_gets_mention_rank() -> None:
    subject = _subject_with_beta()
    drafts, competitors = build_mention_entity_signals("ignored", subject=subject, url_hosts=[])
    own = own_draft(drafts)
    own.mentioned = False
    own.mention_count = 0
    own.rank_hint_first_index = None

    text = "综合对比后更推荐 Aperix。"
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "Aperix": {
                "mentioned": True,
                "score": 90,
                "evidence": "更推荐 Aperix",
            },
            "Beta": {"mentioned": False},
        },
    }
    apply_absa_to_drafts(
        drafts,
        response_absa,
        own_brand="Aperix",
        own_absa_keys=[("Aperix", "Aperix")],
        competitor_absa_keys=[("Beta", "beta.com")],
        competitors=competitors,
        text=text,
    )
    compute_mention_ranks(drafts)

    assert own.mentioned is True
    assert own.mention_rank == 1
    assert own.rank_hint_first_index is not None


def test_absa_denial_clears_mention_rank() -> None:
    subject = _subject_with_beta()
    text = "推荐 Aperix 与 Beta。"
    drafts, competitors = build_mention_entity_signals(text, subject=subject, url_hosts=[])
    comp = draft_for_entity_label(drafts, "beta.com")
    assert comp is not None
    assert comp.mention_rank is not None

    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "Aperix": {"mentioned": True, "score": 75},
            "Beta": {"mentioned": False},
        },
    }
    apply_absa_to_drafts(
        drafts,
        response_absa,
        own_brand="Aperix",
        own_absa_keys=[("Aperix", "Aperix")],
        competitor_absa_keys=[("Beta", "beta.com")],
        competitors=competitors,
        text=text,
    )
    compute_mention_ranks(drafts)

    assert comp.mentioned is False
    assert comp.mention_rank is None
