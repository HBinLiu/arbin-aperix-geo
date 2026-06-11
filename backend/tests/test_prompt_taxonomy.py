"""Prompt taxonomy helpers."""

from __future__ import annotations

import pytest

from aperix_geo.services.prompts.taxonomy import (
    normalize_funnel_stage,
    normalize_search_intent,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("tofu", "tofu"),
        ("BOFU", "bofu"),
        ("invalid", "mofu"),
        (None, "mofu"),
    ],
)
def test_normalize_funnel_stage(raw: str | None, expected: str) -> None:
    assert normalize_funnel_stage(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("informational", "informational"),
        ("transactional", "transactional"),
        ("navigational", "commercial"),
        ("", "commercial"),
    ],
)
def test_normalize_search_intent(raw: str | None, expected: str) -> None:
    assert normalize_search_intent(raw) == expected
