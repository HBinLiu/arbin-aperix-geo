"""Tests for response ABSA cache keys and ABSA failure degradation."""

from __future__ import annotations

import uuid

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.sampling.cache.absa import (
    clear_response_absa_cache,
    get_response_absa_cached,
    response_absa_cache_digest,
    set_response_absa_cached,
)
from aperix_geo.services.sampling.sentiment import apply_response_absa_to_drafts, degrade_absa_failure
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft, init_entity_signal_drafts


def test_absa_cache_hit_by_scope() -> None:
    clear_response_absa_cache()
    text = "推荐 Aperix 与 Stripe"

    set_response_absa_cached(
        raw_text=text,
        own_brand="Aperix",
        competitors=["Beta"],
        result={"analysis_source": "llm", "brands_sentiment_absa": {}, "other_brands_sentiment_absa": {}},
        ttl_s=3600,
    )
    assert get_response_absa_cached(
        raw_text=text,
        own_brand="Aperix",
        competitors=["Beta"],
        ttl_s=3600,
    ) is not None
    assert get_response_absa_cached(
        raw_text=text,
        own_brand="Aperix",
        competitors=["Gamma"],
        ttl_s=3600,
    ) is None


def test_absa_cache_digest_stable_for_same_scope() -> None:
    a = response_absa_cache_digest(
        raw_text="推荐 Aperix",
        own_brand="Aperix",
        competitors=["Beta"],
    )
    b = response_absa_cache_digest(
        raw_text="推荐 Aperix",
        own_brand="Aperix",
        competitors=["Beta"],
    )
    assert a == b


def _subject() -> Subject:
    subject_id = uuid.uuid4()
    subject = Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        domain="aperix.com",
    )
    subject.competitors = [
        Competitor(
            id=uuid.uuid4(),
            subject_id=subject_id,
            brand="Beta",
            domain="beta.com",
        )
    ]
    return subject


def test_absa_failure_keeps_text_mentions_clears_sentiment() -> None:
    drafts = init_entity_signal_drafts(_subject())
    own = next(d for d in drafts if d.entity_kind == "own")
    own.mentioned = True
    own.mention_count = 2
    own.rank_hint_first_index = 0
    own.sentiment_score = 88.0
    own.sentiment_reason = "should clear"

    response_absa = {"analysis_source": "failed", "failure_reason": "timeout"}

    source, _ = apply_response_absa_to_drafts(
        drafts,
        response_absa,
        own_brand="Aperix",
        competitor_brand_names=["Beta"],
        competitor_absa_keys=[("Beta", "beta.com")],
        text="推荐 Aperix 与 Beta",
    )

    assert source == "failed"
    assert own.mentioned is True
    assert own.mention_count == 2
    assert own.sentiment_score is None
    assert own.sentiment_reason is None
    assert own.mention_rank == 1


def test_degrade_absa_failure_recomputes_ranks() -> None:
    drafts = [
        EntitySignalDraft(
            entity_id="own",
            entity_kind="own",
            entity_label="Aperix",
            mentioned=True,
            mention_count=1,
            rank_hint_first_index=10,
            sentiment_score=50.0,
        ),
        EntitySignalDraft(
            entity_id="other:stripe",
            entity_kind="other",
            entity_label="Stripe",
            mentioned=True,
            mention_count=1,
            rank_hint_first_index=0,
            sentiment_score=70.0,
        ),
    ]
    degrade_absa_failure(drafts)
    stripe = next(d for d in drafts if d.entity_kind == "other")
    own = next(d for d in drafts if d.entity_kind == "own")
    assert stripe.mention_rank == 1
    assert own.mention_rank == 2
    assert stripe.sentiment_score is None
    assert own.sentiment_score is None
