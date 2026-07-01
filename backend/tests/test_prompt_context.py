"""Tests for prompt generation context helpers."""

from __future__ import annotations

import uuid

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.prompts.context import entity_aliases, prompt_context_from_subject


def test_entity_aliases_excludes_entity_and_dedupes() -> None:
    aliases = entity_aliases(
        entity="Aperix",
        configured=["Aperix", "aperix.com", "艾佩克斯"],
        profile_company="Aperix Tech",
    )
    assert aliases == ["aperix.com", "艾佩克斯", "Aperix Tech"]


def test_prompt_context_from_subject_uses_niche_profile() -> None:
    subject_id = uuid.uuid4()
    subject = Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        domain="aperix.com",
        aliases=["艾佩克斯"],
        profile_summary="# long summary",
        niche_profile={
            "company": "Aperix",
            "industry": "GEO SaaS",
            "features": "AI可见度监测",
            "customers": "市场团队",
            "category_terms": "AI可见度监测",
        },
    )
    subject.competitors = [
        Competitor(id=uuid.uuid4(), subject_id=subject_id, brand="Beta", domain="beta.com"),
    ]
    ctx = prompt_context_from_subject(subject)
    assert ctx["entity"] == "Aperix"
    assert ctx["features"] == "AI可见度监测"
    assert ctx["industry"] == "GEO SaaS"
    assert ctx["customers"] == "市场团队"
    assert ctx["profile"]["company"] == "Aperix"
    assert "beta.com" in ctx["competitors"]
    assert "Beta" in ctx["competitors"]


def test_prompt_context_falls_back_to_profile_summary() -> None:
    subject = Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        domain="aperix.com",
        profile_summary="# long summary",
        niche_profile={},
    )
    ctx = prompt_context_from_subject(subject)
    assert ctx["features"] == "# long summary"
