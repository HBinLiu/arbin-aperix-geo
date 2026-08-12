"""Tests for setup prompt generation."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.prompts.constants import PROMPT_PER_TOPIC
from aperix_geo.services.prompts.setup import generate_setup_prompts
from aperix_geo.services.setup.cache.prompts import prompts_generation_hash
from aperix_geo.services.setup.topic_items import topic_name_key

_DIMENSIONS = [
    "category_awareness",
    "scenario_fit",
    "solution_comparison",
    "trust_risk",
    "price_value",
]


@pytest.fixture
def _empty_seed_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def _empty_seeds(*, topics, **kwargs):
        return [{"topic": topic, "prompts": []} for topic in topics]

    monkeypatch.setattr(
        "aperix_geo.services.prompts.setup.build_prompts_from_plan",
        _empty_seeds,
    )


def _prompt_profile(*, topic: str = "跨境支付") -> NicheProfile:
    return normalize_niche_profile(
        {
            "industry": "金融科技",
            "keywords": [topic, "跨境收款", "全球账户"],
            "brief": "出海企业",
        },
        entity="example.com",
    )


def _prompt(i: int) -> dict[str, str]:
    return {
        "text": f"问句{i}怎么选合适方案呢",
        "funnel": "mofu" if i % 2 else "tofu",
        "intent": "commercial" if i % 2 else "informational",
        "decision": _DIMENSIONS[i % len(_DIMENSIONS)],
    }


@patch("aperix_geo.services.prompts.setup.chat_completion")
def test_generate_setup_prompts_llm(mock_chat) -> None:
    payload = {
        "topics": [
            {
                "topic": "跨境支付",
                "prompts": [_prompt(i) for i in range(PROMPT_PER_TOPIC)],
            }
        ]
    }
    mock_chat.return_value = (json.dumps(payload), "deepseek", 100.0)

    rows = generate_setup_prompts(
        entity="example.com",
        topics=["跨境支付"],
        profile=_prompt_profile(),
    )
    assert len(rows) == 1
    assert rows[0]["topic"] == "跨境支付"
    assert len(rows[0]["prompts"]) == PROMPT_PER_TOPIC
    assert rows[0]["prompts"][0]["text"] == "问句0怎么选合适方案呢"
    assert rows[0]["prompts"][0]["funnel_stage"] == "tofu"
    assert rows[0]["prompts"][0]["search_intent"] == "informational"
    assert rows[0]["prompts"][0]["decision_type"] == "category_awareness"


@patch("aperix_geo.services.prompts.setup.chat_completion")
def test_generate_setup_prompts_passes_exclude_prompts(mock_chat) -> None:
    payload = {
        "topics": [
            {
                "topic": "支付",
                "prompts": [
                    {
                        "text": "支付怎么选合适",
                        "funnel": "tofu",
                        "intent": "informational",
                        "decision": "scenario_fit",
                    }
                ],
            }
        ]
    }
    mock_chat.return_value = (json.dumps(payload), "deepseek", 100.0)

    generate_setup_prompts(
        entity="Acme",
        topics=["支付"],
        profile=_prompt_profile(topic="支付"),
        exclude_prompts=["已有问题", "  "],
    )

    user_content = mock_chat.call_args[0][0][1]["content"]
    assert '"exclude_prompts": [\n    "已有问题"\n  ]' in user_content
    assert "region" not in user_content
    assert "language" not in user_content


@patch("aperix_geo.services.prompts.setup.chat_completion")
def test_generate_setup_prompts_raises_on_llm_error(mock_chat, _empty_seed_fallback) -> None:
    mock_chat.side_effect = ValueError("missing topics array")

    with pytest.raises(ValueError):
        generate_setup_prompts(
            entity="Acme",
            topics=["支付"],
            profile=_prompt_profile(topic="支付"),
        )


@patch("aperix_geo.services.prompts.setup.chat_completion")
def test_generate_setup_prompts_falls_back_to_plan(mock_chat) -> None:
    mock_chat.side_effect = ValueError("missing topics array")

    rows = generate_setup_prompts(
        entity="Acme",
        topics=["跨境支付"],
        profile=_prompt_profile(topic="跨境支付"),
        prompts_per_topic=PROMPT_PER_TOPIC,
    )
    assert len(rows) == 1
    assert len(rows[0]["prompts"]) == PROMPT_PER_TOPIC
    assert all("跨境支付" in p["text"] for p in rows[0]["prompts"])


@patch("aperix_geo.services.prompts.setup.chat_completion")
def test_generate_setup_prompts_fills_gaps_from_plan(mock_chat) -> None:
    payload = {
        "topics": [
            {
                "topic": "跨境支付",
                "prompts": [
                    {
                        "text": "跨境支付怎么选合适",
                        "funnel": "mofu",
                        "intent": "commercial",
                        "decision": "scenario_fit",
                    }
                ],
            }
        ]
    }
    mock_chat.return_value = (json.dumps(payload), "deepseek", 100.0)

    rows = generate_setup_prompts(
        entity="Acme",
        topics=["跨境支付"],
        profile=_prompt_profile(topic="跨境支付"),
        prompts_per_topic=PROMPT_PER_TOPIC,
    )
    assert len(rows[0]["prompts"]) == PROMPT_PER_TOPIC


@patch("aperix_geo.services.prompts.setup.chat_completion")
def test_generate_setup_prompts_filters_excluded_text(mock_chat) -> None:
    payload = {
        "topics": [
            {
                "topic": "支付",
                "prompts": [
                    {
                        "text": "已有问题",
                        "funnel": "tofu",
                        "intent": "informational",
                        "decision": "scenario_fit",
                    },
                    {
                        "text": "新问题怎么选",
                        "funnel": "mofu",
                        "intent": "commercial",
                        "decision": "price_value",
                    },
                ],
            }
        ]
    }
    mock_chat.return_value = (json.dumps(payload), "deepseek", 100.0)

    rows = generate_setup_prompts(
        entity="Acme",
        topics=["支付"],
        profile=_prompt_profile(topic="支付"),
        prompts_per_topic=2,
        exclude_prompts=["已有问题"],
    )
    texts = [p["text"] for p in rows[0]["prompts"]]
    assert "已有问题" not in texts
    assert "新问题怎么选" in texts


@patch("aperix_geo.services.prompts.setup.chat_completion")
def test_generate_setup_prompts_topic_key_match(mock_chat) -> None:
    batch = {
        "topics": [
            {
                "topic": "AI搜索可见度",
                "prompts": [
                    {
                        "text": "AI搜索可见度怎么选",
                        "funnel": "tofu",
                        "intent": "informational",
                        "decision": "category_awareness",
                    }
                ],
            }
        ]
    }
    mock_chat.return_value = (json.dumps(batch), "deepseek", 100.0)

    rows = generate_setup_prompts(
        entity="Acme",
        topics=["AI 搜索可见度", "跨境支付"],
        profile=_prompt_profile(),
        prompts_per_topic=1,
    )
    by_topic = {row["topic"]: row["prompts"][0]["text"] for row in rows}
    assert topic_name_key("AI 搜索可见度") == topic_name_key("AI搜索可见度")
    assert by_topic["AI 搜索可见度"] == "AI搜索可见度怎么选"
    assert by_topic["跨境支付"]
    assert mock_chat.call_count == 1


def test_prompts_generation_hash_uses_topic_name_key() -> None:
    base = dict(
        entity="example.com",
        competitors=["rival.com"],
        industry="SaaS",
        keywords="API",
        brief="团队",
        aliases=["Example"],
        exclude_prompts=[],
    )
    assert prompts_generation_hash(topics=["AI 可见度"], **base) == prompts_generation_hash(
        topics=["AI可见度"], **base
    )


@patch("aperix_geo.services.prompts.setup.chat_completion")
def test_generate_setup_prompts_preserves_punctuation(mock_chat) -> None:
    payload = {
        "topics": [
            {
                "topic": "跨境支付",
                "prompts": [
                    {
                        "text": "跨境收款怎么选？",
                        "funnel": "mofu",
                        "intent": "commercial",
                        "decision": "category_awareness",
                    },
                    _prompt(1),
                    _prompt(2),
                    _prompt(3),
                ],
            }
        ]
    }
    mock_chat.return_value = (json.dumps(payload), "deepseek", 100.0)

    rows = generate_setup_prompts(
        entity="Acme",
        topics=["跨境支付"],
        profile=_prompt_profile(),
        prompts_per_topic=4,
    )
    texts = [p["text"] for p in rows[0]["prompts"]]
    assert "跨境收款怎么选？" in texts
