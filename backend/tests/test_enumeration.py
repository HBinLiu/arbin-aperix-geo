"""Tests for enumeration span extraction and ABSA prompt hints."""

from __future__ import annotations

from aperix_geo.services.providers.prompts import citation_response_absa_user_content
from aperix_geo.services.sampling.enumeration import extract_enumerated_spans


def test_extract_enumerated_spans_from_parenthetical_list() -> None:
    text = "核心西药包括他汀类（阿托伐他汀、瑞舒伐他汀、辛伐他汀等），需遵医嘱。"
    assert extract_enumerated_spans(text) == [
        "阿托伐他汀",
        "瑞舒伐他汀",
        "辛伐他汀",
    ]


def test_extract_enumerated_spans_antiplatelet_pair() -> None:
    text = "抗血小板药（阿司匹林、氯吡格雷）有出血风险。"
    assert extract_enumerated_spans(text) == ["阿司匹林", "氯吡格雷"]


def test_extract_enumerated_spans_slash_separated() -> None:
    text = "中成药（银杏酮酯/杏灵分散片等）仅作辅助。"
    assert extract_enumerated_spans(text) == ["银杏酮酯", "杏灵分散片"]


def test_extract_enumerated_spans_english_commas() -> None:
    text = "Payment tools (Stripe, PayPal, Square) are common."
    spans = extract_enumerated_spans(text)
    assert spans == ["Stripe", "PayPal", "Square"]


def test_extract_enumerated_spans_skips_single_item_parentheses() -> None:
    text = "详见附录（附录一）与说明（仅供参考）。"
    assert extract_enumerated_spans(text) == []


def test_extract_enumerated_spans_skips_urls() -> None:
    text = "访问（https://example.com/a、https://example.com/b）无效。"
    assert extract_enumerated_spans(text) == []


def test_extract_enumerated_spans_deduplicates() -> None:
    text = "推荐（Stripe、PayPal）与 Stripe/PayPal 组合。"
    spans = extract_enumerated_spans(text)
    assert spans == ["Stripe", "PayPal"]


def test_citation_response_absa_user_content_includes_enumeration_block() -> None:
    raw_text = "抗血小板药（阿司匹林、氯吡格雷）需评估出血风险。"
    content = citation_response_absa_user_content(
        raw_text=raw_text,
        own_brand="杏灵分散片",
        own_brand_names=["杏灵分散片"],
        competitor_brand_names=[],
    )
    assert "# 正文提及候选（规则列举 + Discovery，须逐条核对开集规则）" in content
    assert "  - 阿司匹林" in content
    assert "  - 氯吡格雷" in content


def test_citation_response_absa_user_content_omits_empty_enumeration_block() -> None:
    content = citation_response_absa_user_content(
        raw_text="推荐 Aperix 作为首选。",
        own_brand="Aperix",
        own_brand_names=["Aperix"],
        competitor_brand_names=["Beta"],
    )
    assert "# 正文提及候选" not in content
