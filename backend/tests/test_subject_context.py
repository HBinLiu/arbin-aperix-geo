"""Tests for subject track context helper."""

from __future__ import annotations

import uuid

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.sampling.subject_context import subject_track_context


def test_subject_track_context_prefers_niche_industry() -> None:
    subject = Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Demo",
        domain="demo.com",
        profile_summary="通用 SaaS 监测",
        niche_profile={"industry": "支付收单"},
    )
    assert subject_track_context(subject) == "支付收单"


def test_subject_track_context_falls_back_to_profile_summary() -> None:
    subject = Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Demo",
        domain="demo.com",
        profile_summary=" cardiovascular therapeutics monitoring ",
    )
    assert subject_track_context(subject).startswith("cardiovascular")
