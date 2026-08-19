"""Tests for candidate-based open-set mention fallback."""

from __future__ import annotations

import uuid

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.brand.keys import configured_brand_keys
from aperix_geo.services.sampling.enumeration import merge_mention_candidates
from aperix_geo.services.sampling.sentiment import (
    append_candidate_mention_drafts,
    apply_response_absa_to_drafts,
)
from aperix_geo.services.sampling.signal_draft import init_entity_signal_drafts


def _subject() -> Subject:
    subject_id = uuid.uuid4()
    subject = Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="杏灵分散片",
        domain="example.com",
    )
    subject.competitors = [
        Competitor(
            id=uuid.uuid4(),
            subject_id=subject_id,
            brand="竞品A",
            domain="comp-a.com",
        )
    ]
    return subject


def test_append_candidate_mention_drafts_fills_missing_enum_items() -> None:
    text = "抗血小板药（阿司匹林、氯吡格雷、替格瑞洛）需评估出血风险。"
    drafts = init_entity_signal_drafts(_subject())
    candidates = merge_mention_candidates(text, [])
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "杏灵分散片": {"mentioned": False, "score": None, "evidence": ""},
            "竞品A": {"mentioned": False, "score": None, "evidence": ""},
        },
        "other_brands_sentiment_absa": {
            "阿司匹林": {"mentioned": True, "score": 50, "evidence": "抗血小板药"},
        },
        "mention_candidates": candidates,
    }
    excluded = configured_brand_keys(
        own_brand="杏灵分散片",
        competitor_brand_names=["竞品A"],
        competitor_absa_keys=[("竞品A", "comp-a.com")],
    )

    append_candidate_mention_drafts(
        drafts,
        response_absa,
        mention_candidates=candidates,
        excluded_keys=excluded,
        text=text,
    )

    labels = {draft.entity_label for draft in drafts if draft.entity_kind == "other"}
    assert "阿司匹林" in labels
    assert "氯吡格雷" in labels
    assert "替格瑞洛" in labels


def test_append_candidate_mention_drafts_respects_absa_denial() -> None:
    text = "可选方案包括 Stripe 与 PayPal。"
    drafts = init_entity_signal_drafts(_subject())
    candidates = ["Stripe", "PayPal"]
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {},
        "other_brands_sentiment_absa": {
            "Stripe": {"mentioned": True, "score": 80, "evidence": "可选 Stripe"},
            "PayPal": {"mentioned": False, "score": None, "evidence": "非竞品"},
        },
    }
    excluded = configured_brand_keys(own_brand="杏灵分散片", competitor_brand_names=["竞品A"])

    append_candidate_mention_drafts(
        drafts,
        response_absa,
        mention_candidates=candidates,
        excluded_keys=excluded,
        text=text,
    )

    labels = {draft.entity_label for draft in drafts if draft.entity_kind == "other"}
    assert "Stripe" in labels
    assert "PayPal" not in labels


def test_apply_response_absa_to_drafts_uses_mention_candidates_from_payload() -> None:
    text = "常用包括（布洛芬、对乙酰氨基酚）。"
    drafts = init_entity_signal_drafts(_subject())
    candidates = merge_mention_candidates(text, [])
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "杏灵分散片": {"mentioned": False},
            "竞品A": {"mentioned": False},
        },
        "other_brands_sentiment_absa": {},
        "mention_candidates": candidates,
    }

    apply_response_absa_to_drafts(
        drafts,
        response_absa,
        own_brand="杏灵分散片",
        competitor_brand_names=["竞品A"],
        competitor_absa_keys=[("竞品A", "comp-a.com")],
        text=text,
    )

    labels = {draft.entity_label for draft in drafts if draft.entity_kind == "other"}
    assert "布洛芬" in labels
    assert "对乙酰氨基酚" in labels
