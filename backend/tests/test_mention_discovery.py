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
    text = "抗血小板药（阿司匹林、氯吡格雷）有出血风险；他汀类需监测。"
    mock_chat.return_value = (
        json.dumps(
            {
                "entities": [
                    {
                        "text": "阿司匹林",
                        "type": "PRODUCT",
                        "start": text.index("阿司匹林"),
                        "end": text.index("阿司匹林") + len("阿司匹林"),
                    },
                    {
                        "text": "氯吡格雷",
                        "type": "PRODUCT",
                        "start": text.index("氯吡格雷"),
                        "end": text.index("氯吡格雷") + len("氯吡格雷"),
                    },
                    {
                        "text": "出血风险",
                        "type": "PRODUCT",
                        "start": text.index("出血风险"),
                        "end": text.index("出血风险") + len("出血风险"),
                    },
                    {
                        "text": "他汀类",
                        "type": "PRODUCT",
                        "start": text.index("他汀类"),
                        "end": text.index("他汀类") + len("他汀类"),
                    },
                ]
            }
        ),
        None,
        None,
    )
    entities, live = discover_response_mentions(text, cache_ttl_s=0)
    assert live is True
    labels = {entity.text for entity in entities}
    assert "阿司匹林" in labels
    assert "氯吡格雷" in labels
    assert "出血风险" not in labels
    assert "他汀类" not in labels


@patch("aperix_geo.services.sampling.response_absa.chat_completion")
@patch("aperix_geo.services.sampling.response_absa.discover_response_mentions")
def test_analyze_response_absa_passes_merged_candidates(mock_discover, mock_absa_chat) -> None:
    from aperix_geo.services.sampling.mention_entities import ValidatedMention

    text = "推荐 Stripe，亦可考虑 PayPal。"
    mock_discover.return_value = (
        [
            ValidatedMention(
                text="PayPal",
                entity_type="PRODUCT",
                start=text.index("PayPal"),
                end=text.index("PayPal") + len("PayPal"),
                source="discovery",
            )
        ],
        True,
    )
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
