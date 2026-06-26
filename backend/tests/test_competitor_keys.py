"""Tests for configured competitor match keys."""

from __future__ import annotations

import uuid

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.competitor.keys import competitor_match_key, find_competitor_conflict


def _subject(*, competitors: list[Competitor] | None = None) -> Subject:
    subject = Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.domain,
        brand="Aperix",
        website_url="https://aperix.com",
        domain="aperix.com",
    )
    subject.competitors = list(competitors or [])
    return subject


def test_competitor_match_key_prefers_domain() -> None:
    assert competitor_match_key(domain="beta.com", brand="Beta") == "d:beta.com"
    assert competitor_match_key(domain="", brand="Beta") == "b:beta"


def test_find_competitor_conflict_detects_domain_and_brand() -> None:
    subject = _subject(
        competitors=[
            Competitor(
                id=uuid.uuid4(),
                subject_id=uuid.uuid4(),
                domain="beta.com",
                website_url="https://beta.com",
                brand="Beta",
            )
        ]
    )

    assert find_competitor_conflict(subject, domain="beta.com", brand="Other") == "该域名已是配置竞品"
    assert find_competitor_conflict(subject, domain="", brand="Beta") == "该品牌已是配置竞品"
    assert find_competitor_conflict(subject, domain="gamma.com", brand="Gamma") is None
