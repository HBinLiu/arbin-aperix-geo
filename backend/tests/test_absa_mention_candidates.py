"""Tests for mention enumeration candidates fed into ABSA."""

from __future__ import annotations

import json
from unittest.mock import patch

from aperix_geo.services.sampling.enumeration import merge_mention_candidates
from aperix_geo.services.sampling.response_absa import analyze_response_absa


def test_merge_mention_candidates_combines_enum_and_extras() -> None:
    text = "抗血小板药（阿司匹林、氯吡格雷）需评估；另需注意银杏酮酯。"
    merged = merge_mention_candidates(text, ["银杏酮酯", "出血风险"])
    assert merged == ["阿司匹林", "氯吡格雷", "银杏酮酯"]


@patch("aperix_geo.services.sampling.response_absa.chat_completion")
def test_analyze_response_absa_uses_enum_candidates(mock_absa_chat) -> None:
    text = "推荐 Stripe，亦可考虑 PayPal。抗血小板药（阿司匹林、氯吡格雷）需评估。"
    mock_absa_chat.return_value = (
        json.dumps(
            {
                "brands_sentiment_absa": {
                    "Aperix": {"mentioned": False, "score": None, "evidence": ""},
                },
                "other_brands_sentiment_absa": {
                    "Stripe": {"mentioned": True, "score": 75, "evidence": "推荐 Stripe"},
                    "PayPal": {"mentioned": True, "score": 70, "evidence": "考虑 PayPal"},
                    "阿司匹林": {"mentioned": True, "score": 60, "evidence": "阿司匹林"},
                },
            }
        ),
        None,
        None,
    )

    result, live = analyze_response_absa(
        text,
        own_brand="Aperix",
        competitors=["Aperix"],
        cache_ttl_s=0,
    )

    user_content = mock_absa_chat.call_args[0][0][1]["content"]
    assert "  - 阿司匹林" in user_content
    assert "  - 氯吡格雷" in user_content
    assert "discovery_entities" not in result
    assert result["other_brands_sentiment_absa"]["Stripe"]["mentioned"] is True
    assert live is True
