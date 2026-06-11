"""Tests for entity signal match_terms enrichment."""

from __future__ import annotations

import uuid

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.analysis.entity import OWN_ENTITY_ID
from aperix_geo.services.sampling.signals.match import match_terms_for_entity_signal


def _subject(*, aliases: list[str] | None = None) -> Subject:
    subject_id = uuid.uuid4()
    subject = Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        domain="aperix.com",
        aliases=aliases or ["APX"],
    )
    subject.competitors = [
        Competitor(
            id=uuid.uuid4(),
            subject_id=subject_id,
            brand="Beta",
            domain="beta.com",
            aliases=["BetaCorp"],
        )
    ]
    return subject


def test_match_terms_own_includes_aliases() -> None:
    subject = _subject()
    terms = match_terms_for_entity_signal(
        subject,
        entity_id=OWN_ENTITY_ID,
        entity_kind="own",
        entity_label="Aperix",
        primary_domain="aperix.com",
    )
    assert "Aperix" in terms
    assert "aperix.com" in terms
    assert "APX" in terms


def test_match_terms_competitor_includes_aliases() -> None:
    subject = _subject()
    competitor_id = subject.competitors[0].id
    terms = match_terms_for_entity_signal(
        subject,
        entity_id=str(competitor_id),
        entity_kind="competitor",
        entity_label="Beta",
        primary_domain="beta.com",
    )
    assert "Beta" in terms
    assert "beta.com" in terms
    assert "BetaCorp" in terms


def test_match_terms_other_uses_label_and_domain() -> None:
    subject = _subject()
    terms = match_terms_for_entity_signal(
        subject,
        entity_id="other:gamma",
        entity_kind="other",
        entity_label="Gamma",
        primary_domain="gamma.io",
    )
    assert terms == ["Gamma", "gamma.io"]
