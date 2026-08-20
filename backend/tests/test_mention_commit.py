"""Tests for mention commit gate and commit plan."""

from __future__ import annotations

from aperix_geo.services.sampling.mention_commit import (
    MentionEntityInput,
    build_mention_commit_plan,
    validate_mention_entity,
)


MEDICAL_TEXT = (
    "### 1.他汀类（阿托伐他汀、瑞舒伐他汀等）\n"
    "### 2.抗血小板（阿司匹林、氯吡格雷）\n"
    "## 二、中成药（如杏灵分散片/银杏酮酯，辅助改善头晕）\n"
    "所有用药务必遵从神经内科、心内科医生方案；避免大量西柚。出血史需告知医生。"
)


def test_validate_mention_entity_rejects_sentence_fragment() -> None:
    text = "所有用药务必遵从神经内科、心内科医生方案；避免大量西柚。出血史需告知医生。"
    for fragment in ("所有用药务必遵从神经内科", "避免大量西柚", "出血史"):
        assert (
            validate_mention_entity(
                text,
                MentionEntityInput(text=fragment, entity_type="PRODUCT", source="enum"),
            )
            is None
        )


def test_validate_mention_entity_accepts_product_name() -> None:
    text = MEDICAL_TEXT
    ok = validate_mention_entity(
        text,
        MentionEntityInput(text="阿托伐他汀", entity_type="PRODUCT", source="enum"),
    )
    assert ok is not None
    assert ok.text == "阿托伐他汀"
    assert text[ok.start : ok.end] == "阿托伐他汀"


def test_build_mention_commit_plan_enum_commits_without_absa() -> None:
    text = "抗血小板药（阿司匹林、氯吡格雷、替格瑞洛）需评估。"
    response_absa = {
        "other_brands_sentiment_absa": {
            "阿司匹林": {
                "mentioned": True,
                "score": 70,
                "evidence": "抗血小板药",
                "entity_type": "PRODUCT",
            },
        }
    }
    plan = build_mention_commit_plan(text, response_absa, excluded_keys=set())
    committed = {event.text for event in plan.committed()}
    assert "阿司匹林" in committed
    assert "氯吡格雷" in committed
    assert "替格瑞洛" in committed
    assert "抗血小板" not in committed


def test_build_mention_commit_plan_enum_without_absa_is_committed() -> None:
    text = "抗血小板药（阿司匹林、氯吡格雷）需评估。"
    plan = build_mention_commit_plan(
        text,
        {"other_brands_sentiment_absa": {}},
        excluded_keys=set(),
    )
    committed = {event.text for event in plan.committed()}
    assert "阿司匹林" in committed
    assert "氯吡格雷" in committed


def test_build_mention_commit_plan_dismisses_absa_denial() -> None:
    text = "可选 Stripe 与 PayPal。"
    plan = build_mention_commit_plan(
        text,
        {
            "other_brands_sentiment_absa": {
                "PayPal": {"mentioned": False, "evidence": "非竞品"},
            }
        },
        excluded_keys=set(),
    )
    assert any(event.text == "PayPal" and event.status == "dismissed" for event in plan.events)
    assert "PayPal" not in {event.text for event in plan.committed()}


def test_build_mention_commit_plan_matches_absa_by_normalized_key() -> None:
    text = "可选 Stripe 与 paypal。"
    plan = build_mention_commit_plan(
        text,
        {
            "other_brands_sentiment_absa": {
                "PayPal": {"mentioned": True, "score": 70, "evidence": "paypal"},
            }
        },
        excluded_keys=set(),
    )
    committed = {event.text.casefold() for event in plan.committed()}
    assert "paypal" in committed
