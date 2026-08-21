"""Tests for mention span normalization and noise filtering."""

from __future__ import annotations

from aperix_geo.services.sampling.enumeration import (
    filter_mention_spans,
    is_plausible_commercial_span,
    merge_mention_candidates,
    normalize_mention_span,
)


def test_normalize_mention_span_strips_leading_junk_and_trailing_clause() -> None:
    assert normalize_mention_span("如杏灵分散片") == "杏灵分散片"
    assert normalize_mention_span("银杏酮酯，辅助改善头晕") == "银杏酮酯"


def test_is_plausible_commercial_span_rejects_medical_noise() -> None:
    noise = [
        "他汀",
        "抗血小板",
        "牙龈",
        "皮肤出血",
        "出血史",
        "出血风险",
        "如果同时吃阿司匹林",
        "肝功能异常",
        "肝病",
        "胃病",
        "肝炎",
        "肾病",
        "糖尿病",
        "降压降糖",
        "有没有胃病",
        "所有用药务必遵从神经内科",
        "心内科医生方案",
        "避免大量西柚",
        "神经内科",
    ]
    for label in noise:
        assert is_plausible_commercial_span(label) is False, label

    valid = ["阿托伐他汀", "瑞舒伐他汀", "阿司匹林", "氯吡格雷", "杏灵分散片", "银杏酮酯", "腾讯"]
    for label in valid:
        assert is_plausible_commercial_span(label) is True, label


def test_filter_mention_spans_cleans_discovery_garbage() -> None:
    text = "中成药（杏灵分散片/银杏酮酯）可辅助改善头晕；抗血小板（阿司匹林、氯吡格雷）需评估。"
    spans = filter_mention_spans(
        [
            "他汀",
            "抗血小板",
            "如杏灵分散片",
            "银杏酮酯，辅助改善头晕",
            "阿司匹林",
            "氯吡格雷",
            "皮肤出血",
            "出血史",
            "出血风险",
            "有没有胃病",
        ],
        text,
    )
    assert spans == ["杏灵分散片", "银杏酮酯", "阿司匹林", "氯吡格雷"]


def test_filter_mention_spans_rejects_advisory_fragments() -> None:
    text = "所有用药务必遵从神经内科、心内科医生方案；避免大量西柚。"
    spans = filter_mention_spans(
        [
            "所有用药务必遵从神经内科",
            "心内科医生方案",
            "避免大量西柚",
            "神经内科",
        ],
        text,
    )
    assert spans == []


def test_merge_mention_candidates_keeps_only_product_names_from_article() -> None:
    text = (
        "### 1.他汀类（阿托伐他汀、瑞舒伐他汀等）\n"
        "### 2.抗血小板（阿司匹林、氯吡格雷）\n"
        "## 二、中成药（如杏灵分散片/银杏酮酯，辅助改善头晕）"
    )
    merged = merge_mention_candidates(
        text,
        ["他汀", "抗血小板", "牙龈", "皮肤出血", "如果同时吃阿司匹林", "肝功能异常"],
    )
    labels = set(merged)
    assert {"阿托伐他汀", "瑞舒伐他汀", "阿司匹林", "氯吡格雷", "杏灵分散片", "银杏酮酯"} <= labels
    assert "他汀" not in labels
    assert "抗血小板" not in labels
    assert "牙龈" not in labels
    assert "皮肤出血" not in labels
