"""Tests for open-set ABSA draft append."""

from __future__ import annotations

import uuid

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.brand.keys import configured_brand_keys
from aperix_geo.services.sampling.sentiment import append_other_brand_drafts, apply_response_absa_to_drafts
from aperix_geo.services.sampling.signal_draft import compute_mention_ranks, init_entity_signal_drafts


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


def test_append_other_brand_drafts() -> None:
    drafts = init_entity_signal_drafts(_subject())
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {},
        "other_brands_sentiment_absa": {
            "Stripe": {
                "mentioned": True,
                "score": 0.6,
                "framing_tags": [],
                "evidence": "推荐 Stripe",
            },
            "Aperix": {"mentioned": True, "score": 0.9},
        },
    }
    excluded = configured_brand_keys(
        own_brand="Aperix",
        competitor_brand_names=["Beta"],
        competitor_absa_keys=[("Beta", "beta.com")],
    )
    append_other_brand_drafts(drafts, response_absa, excluded_keys=excluded)

    others = [draft for draft in drafts if draft.entity_kind == "other"]
    assert len(others) == 1
    assert others[0].entity_label == "Stripe"
    assert others[0].sentiment_score == 80.0


def test_append_other_brand_drafts_sets_mention_rank_from_text() -> None:
    drafts = init_entity_signal_drafts(_subject())
    text = "推荐 Stripe 与 Aperix，Beta 也可考虑。"
    for draft in drafts:
        if draft.entity_label == "aperix.com":
            draft.rank_hint_first_index = text.lower().find("aperix")
        if draft.entity_label == "beta.com":
            draft.rank_hint_first_index = text.lower().find("beta")

    response_absa = {
        "other_brands_sentiment_absa": {
            "Stripe": {"mentioned": True, "score": 0.5, "evidence": "推荐 Stripe"},
        }
    }
    append_other_brand_drafts(
        drafts,
        response_absa,
        excluded_keys=configured_brand_keys(
            own_brand="Aperix",
            competitor_brand_names=["Beta"],
            competitor_absa_keys=[("Beta", "beta.com")],
        ),
        text=text,
    )
    compute_mention_ranks(drafts)

    stripe = next(draft for draft in drafts if draft.entity_label == "Stripe")
    aperix = next(draft for draft in drafts if draft.entity_kind == "own")
    beta = next(draft for draft in drafts if draft.entity_label == "beta.com")

    assert stripe.mention_rank == 1
    assert aperix.mention_rank == 2
    assert beta.mention_rank == 3
    assert stripe.mention_count == 1


def test_append_other_brand_drafts_sets_has_domain_link() -> None:
    drafts = init_entity_signal_drafts(_subject())
    text = "推荐 Stripe（https://stripe.com/payments）用于跨境收款。"
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {},
        "other_brands_sentiment_absa": {
            "Stripe": {"mentioned": True, "score": 0.5, "evidence": "推荐 Stripe"},
        },
    }
    apply_response_absa_to_drafts(
        drafts,
        response_absa,
        own_brand="Aperix",
        competitor_brand_names=["Beta"],
        competitor_absa_keys=[("Beta", "beta.com")],
        text=text,
        url_hosts=["stripe.com"],
    )
    stripe = next(draft for draft in drafts if draft.entity_label == "Stripe")
    assert stripe.has_domain_link is True
