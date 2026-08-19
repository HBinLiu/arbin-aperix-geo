"""Tests for mention discovery and ABSA integration."""

from __future__ import annotations

import json
from unittest.mock import patch

from aperix_geo.services.sampling.enumeration import merge_mention_candidates
from aperix_geo.services.sampling.mentions import discover_response_mentions
from aperix_geo.services.sampling.response_absa import analyze_response_absa


def test_merge_mention_candidates_combines_enum_and_discovery() -> None:
    text = "抗血小板药（阿司匹林、氯吡格雷）需评估；另需注意银杏酮酯。"
    merged = merge_mention_candidates(text, ["银杏酮酯", "出血风险"])
    assert merged == ["阿司匹林", "氯吡格雷", "银杏酮酯"]


@patch("aperix_geo.services.sampling.mentions.chat_completion")
def test_discover_response_mentions_filters_noise(mock_chat) -> None:
    mock_chat.return_value = (
        json.dumps(
            {
                "mentioned_spans": [
                    "阿司匹林",
                    "氯吡格雷",
                    "出血风险",
                    "他汀类",
                ]
            }
        ),
        None,
        None,
    )
    text = "抗血小板药（阿司匹林、氯吡格雷）有出血风险；他汀类需监测。"
    spans, live = discover_response_mentions(text, cache_ttl_s=0)
    assert live is True
    assert "阿司匹林" in spans
    assert "氯吡格雷" in spans


@patch("aperix_geo.services.sampling.response_absa.chat_completion")
@patch("aperix_geo.services.sampling.response_absa.discover_response_mentions")
def test_analyze_response_absa_passes_merged_candidates(mock_discover, mock_absa_chat) -> None:
    text = "推荐 Stripe，亦可考虑 PayPal。"
    mock_discover.return_value = (["PayPal"], True)
    mock_absa_chat.return_value = (
        json.dumps(
            {
                "brands_sentiment_absa": {
                    "Aperix": {"mentioned": False, "score": None, "evidence": ""},
                },
                "other_brands_sentiment_absa": {
                    "Stripe": {"mentioned": True, "score": 75, "evidence": "推荐 Stripe"},
                    "PayPal": {"mentioned": True, "score": 70, "evidence": "考虑 PayPal"},
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
        mention_discovery_enabled=True,
        mention_discovery_cache_ttl_s=0,
    )

    mock_discover.assert_called_once()
    user_content = mock_absa_chat.call_args[0][0][1]["content"]
    assert "  - PayPal" in user_content
    assert result["other_brands_sentiment_absa"]["Stripe"]["mentioned"] is True
    assert live is True


@patch("aperix_geo.services.sampling.response_absa.discover_response_mentions")
@patch("aperix_geo.services.sampling.response_absa.chat_completion")
def test_analyze_response_absa_skips_discovery_when_disabled(mock_absa_chat, mock_discover) -> None:
    mock_absa_chat.return_value = (
        json.dumps(
            {
                "brands_sentiment_absa": {
                    "Aperix": {"mentioned": True, "score": 80, "evidence": "推荐 Aperix"},
                },
                "other_brands_sentiment_absa": {},
            }
        ),
        None,
        None,
    )
    analyze_response_absa(
        "推荐 Aperix",
        own_brand="Aperix",
        competitors=["Aperix"],
        cache_ttl_s=0,
        mention_discovery_enabled=False,
    )
    mock_discover.assert_not_called()
