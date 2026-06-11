"""Tests for ABSA → entity signal draft sentiment mapping."""

from __future__ import annotations

import uuid

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.analysis.entity import OWN_ENTITY_ID
from aperix_geo.services.sampling.mentions import absa_competitor_keys, competitor_entries
from aperix_geo.services.sampling.sentiment import (
    absa_sentiment_source,
    apply_absa_to_drafts,
    reset_sentiment_drafts,
)
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft, init_entity_signal_drafts
from aperix_geo.utils.sentiment import absa_score_to_label, absa_score_to_points, sentiment_points


def _subject(*, with_competitor: bool = True) -> Subject:
    subject_id = uuid.uuid4()
    subject = Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        domain="aperix.com",
    )
    if with_competitor:
        subject.competitors = [
            Competitor(
                id=uuid.uuid4(),
                subject_id=subject_id,
                brand="Beta",
                domain="beta.com",
            )
        ]
    return subject


def test_absa_score_mapping() -> None:
    assert absa_score_to_points(1.0) == 100.0
    assert absa_score_to_points(0.0) == 50.0
    assert absa_score_to_points(-1.0) == 0.0
    assert absa_score_to_points(0.8) == 90.0
    assert absa_score_to_label(0.8) == "positive"
    assert absa_score_to_label(0.0) == "neutral"
    assert absa_score_to_label(-0.5) == "negative"


def test_competitor_sentiment_cleared_when_not_mentioned() -> None:
    subject = _subject()
    drafts = init_entity_signal_drafts(subject)
    competitors = competitor_entries(subject)
    _, competitor_absa_keys = absa_competitor_keys(competitors)
    comp = next(d for d in drafts if d.entity_kind == "competitor")
    comp.sentiment_label = "positive"
    comp.sentiment_score = 90.0
    comp.sentiment_reason = "old"

    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "Aperix": {"mentioned": True, "score": 0.5},
            "Beta": {"mentioned": False, "score": 0.9, "evidence": "ignored"},
        },
    }
    apply_absa_to_drafts(
        drafts,
        response_absa,
        own_brand="Aperix",
        competitor_absa_keys=competitor_absa_keys,
    )
    assert comp.sentiment_label == "neutral"
    assert comp.sentiment_score is None
    assert comp.sentiment_reason is None


def test_competitor_sentiment_prefers_mentioned_alias_key() -> None:
    subject = _subject()
    drafts = init_entity_signal_drafts(subject)
    competitors = competitor_entries(subject)
    _, competitor_absa_keys = absa_competitor_keys(competitors)

    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "Aperix": {"mentioned": True, "score": 0.5},
            "Beta": {"mentioned": False, "score": 0.9, "evidence": "ignored"},
            "beta.com": {"mentioned": True, "score": 0.2, "evidence": "domain mention"},
        },
    }
    apply_absa_to_drafts(
        drafts,
        response_absa,
        own_brand="Aperix",
        competitor_absa_keys=competitor_absa_keys,
    )
    comp = next(d for d in drafts if d.entity_kind == "competitor")
    assert comp.sentiment_score == 60.0
    assert comp.sentiment_reason == "domain mention"


def test_apply_absa_to_drafts() -> None:
    subject = _subject()
    drafts = init_entity_signal_drafts(subject)
    competitors = competitor_entries(subject)
    _, competitor_absa_keys = absa_competitor_keys(competitors)
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "Aperix": {
                "mentioned": True,
                "score": 0.8,
                "framing_tags": ["稳定"],
                "evidence": "明确推荐 Aperix",
            },
            "Beta": {
                "mentioned": True,
                "score": 0.0,
                "framing_tags": [],
                "evidence": "客观对比 Beta",
            },
        },
    }
    source = apply_absa_to_drafts(
        drafts,
        response_absa,
        own_brand="Aperix",
        competitor_absa_keys=competitor_absa_keys,
    )
    own = next(d for d in drafts if d.entity_id == OWN_ENTITY_ID)
    comp = next(d for d in drafts if d.entity_kind == "competitor")

    assert source == "llm"
    assert own.sentiment_label == "positive"
    assert own.sentiment_score == 90.0
    assert own.sentiment_reason == "明确推荐 Aperix"
    assert comp.sentiment_label == "neutral"
    assert comp.sentiment_score == 50.0
    assert comp.sentiment_reason == "客观对比 Beta"


def test_apply_absa_sentiment_ignores_parser_mentions() -> None:
    """ABSA mention detection drives sentiment even when parser would miss the brand."""
    drafts = init_entity_signal_drafts(_subject(with_competitor=False))
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "阿里健康": {
                "mentioned": True,
                "score": 0.6,
                "framing_tags": [],
                "evidence": "阿里健康在医药电商领域表现突出",
            },
        },
    }
    apply_absa_to_drafts(
        drafts,
        response_absa,
        own_brand="阿里健康",
        competitor_absa_keys=[],
    )
    own = drafts[0]
    assert own.sentiment_label == "positive"
    assert own.sentiment_score == 80.0


def test_apply_absa_sentiment_not_mentioned() -> None:
    drafts = init_entity_signal_drafts(_subject(with_competitor=False))
    response_absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {
            "Aperix": {"mentioned": False, "score": 0.9, "framing_tags": [], "evidence": ""},
        },
    }
    apply_absa_to_drafts(
        drafts,
        response_absa,
        own_brand="Aperix",
        competitor_absa_keys=[],
    )
    own = drafts[0]
    assert own.sentiment_label == "neutral"
    assert own.sentiment_score is None


def test_apply_absa_sentiment_failed() -> None:
    drafts = init_entity_signal_drafts(_subject(with_competitor=False))
    source = apply_absa_to_drafts(
        drafts,
        {"analysis_source": "failed"},
        own_brand="Aperix",
        competitor_absa_keys=[],
    )
    assert source == "failed"
    assert drafts[0].sentiment_score is None


def test_reset_sentiment_drafts() -> None:
    drafts = [
        EntitySignalDraft(
            entity_id=OWN_ENTITY_ID,
            entity_kind="own",
            entity_label="Aperix",
            sentiment_label="positive",
            sentiment_score=90.0,
            sentiment_reason="good",
        )
    ]
    reset_sentiment_drafts(drafts)
    assert drafts[0].sentiment_label == "neutral"
    assert drafts[0].sentiment_score is None
    assert drafts[0].sentiment_reason is None


def test_absa_sentiment_source() -> None:
    assert absa_sentiment_source({}) == "none"
    assert absa_sentiment_source({"analysis_source": "failed"}) == "failed"
    assert absa_sentiment_source({"analysis_source": "llm", "brands_sentiment_absa": {}}) == "llm"


def test_sentiment_points_from_fraction() -> None:
    assert sentiment_points(0.85) == 85.0
    assert sentiment_points(1.0) == 100.0


def test_sentiment_points_from_hundred_scale() -> None:
    assert sentiment_points(72.5) == 72.5
    assert sentiment_points(100) == 100.0
