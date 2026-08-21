"""Tests for mention commit gate integration in sentiment drafts."""

from __future__ import annotations

import uuid

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.sampling.enumeration import merge_mention_candidates
from aperix_geo.services.sampling.sentiment import apply_response_absa_to_drafts
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


def test_apply_response_absa_commits_enum_without_absa() -> None:
    text = "抗血小板药（阿司匹林、氯吡格雷、替格瑞洛）需评估出血风险。"
    drafts = init_entity_signal_drafts(_subject())
    candidates = merge_mention_candidates(text)
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "杏灵分散片": {"mentioned": False, "score": None, "evidence": ""},
            "竞品A": {"mentioned": False, "score": None, "evidence": ""},
        },
        "other_brands_sentiment_absa": {},
        "mention_candidates": candidates,
    }

    _, payload = apply_response_absa_to_drafts(
        drafts,
        response_absa,
        own_brand="杏灵分散片",
        competitor_brand_names=["竞品A"],
        competitor_absa_keys=[("竞品A", "comp-a.com")],
        text=text,
    )

    labels = {draft.entity_label for draft in drafts if draft.entity_kind == "other"}
    assert labels == {"阿司匹林", "氯吡格雷", "替格瑞洛"}
    committed = {event["text"] for event in payload["mention_commit_events"] if event["status"] == "committed"}
    assert committed == {"阿司匹林", "氯吡格雷", "替格瑞洛"}
    aspirin = next(d for d in drafts if d.entity_label == "阿司匹林")
    assert aspirin.sentiment_score is None


def test_apply_response_absa_enum_and_absa_merge() -> None:
    text = "抗血小板药（阿司匹林、氯吡格雷、替格瑞洛）需评估出血风险。"
    drafts = init_entity_signal_drafts(_subject())
    candidates = merge_mention_candidates(text)
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "杏灵分散片": {"mentioned": False, "score": None, "evidence": ""},
            "竞品A": {"mentioned": False, "score": None, "evidence": ""},
        },
        "other_brands_sentiment_absa": {
            "阿司匹林": {"mentioned": True, "score": 70, "evidence": "阿司匹林"},
            "氯吡格雷": {"mentioned": True, "score": 68, "evidence": "氯吡格雷"},
        },
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
    assert "阿司匹林" in labels
    assert "氯吡格雷" in labels
    assert "替格瑞洛" in labels
    aspirin = next(d for d in drafts if d.entity_label == "阿司匹林")
    assert aspirin.sentiment_score == 70.0


def test_apply_response_absa_respects_absa_denial() -> None:
    text = "支付工具（Stripe、PayPal）较常见。"
    drafts = init_entity_signal_drafts(_subject())
    candidates = merge_mention_candidates(text)
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {},
        "other_brands_sentiment_absa": {
            "Stripe": {"mentioned": True, "score": 80, "evidence": "较常见 Stripe"},
            "PayPal": {"mentioned": False, "score": None, "evidence": "非竞品"},
        },
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
    assert "PayPal" not in labels
    assert "Stripe" in labels
