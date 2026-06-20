"""Tests for prompt performance pagination and search."""

from __future__ import annotations

from aperix_geo.services.analysis.performance import (
    _apply_prompt_search,
    _paginate_prompt_rows,
    _sort_prompt_metric_rows,
)


def _row(*, prompt_text: str, topic_name: str, visibility_rate: float) -> dict:
    return {
        "prompt_id": prompt_text,
        "prompt_text": prompt_text,
        "topic_name": topic_name,
        "visibility_rate": visibility_rate,
        "average_rank": None,
    }


def test_apply_prompt_search_matches_prompt_or_topic() -> None:
    rows = [
        _row(prompt_text="Aperix 推荐", topic_name="品牌", visibility_rate=0.8),
        _row(prompt_text="行业趋势", topic_name="Aperix 对比", visibility_rate=0.5),
        _row(prompt_text="无关内容", topic_name="其他", visibility_rate=0.2),
    ]
    filtered = _apply_prompt_search(rows, "aperix")
    assert len(filtered) == 2


def test_sort_and_paginate_prompt_rows() -> None:
    rows = [
        _row(prompt_text="a", topic_name="t1", visibility_rate=0.2),
        _row(prompt_text="b", topic_name="t2", visibility_rate=0.9),
        _row(prompt_text="c", topic_name="t3", visibility_rate=0.5),
    ]
    sorted_rows = _sort_prompt_metric_rows(rows, sort_by=None, order="desc")
    page_items, total, page, page_size = _paginate_prompt_rows(sorted_rows, page=2, page_size=2)
    assert total == 3
    assert page == 2
    assert page_size == 2
    assert len(page_items) == 1
    assert page_items[0]["prompt_text"] == "a"
