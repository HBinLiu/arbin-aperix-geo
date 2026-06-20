"""Tests for citation page GEO brand scope tightening."""

from __future__ import annotations

import uuid

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.analysis.entity import OWN_ENTITY_ID
from aperix_geo.services.sampling.citation.scope import page_geo_brand_scope
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft, init_entity_signal_drafts
from aperix_geo.services.sampling.mentions import competitor_entries


def _subject_with_competitor(*, brand: str = "Beta") -> Subject:
    subject_id = uuid.uuid4()
    subject = Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        domain="aperix.com",
        website_url="https://aperix.com",
    )
    subject.competitors = [
        Competitor(
            id=uuid.uuid4(),
            subject_id=subject_id,
            brand=brand,
            domain=f"{brand.lower()}.com",
        )
    ]
    return subject


def test_page_geo_brand_scope_only_response_mentioned_competitors() -> None:
    subject = _subject_with_competitor()
    drafts = init_entity_signal_drafts(subject)
    competitors = competitor_entries(subject)
    comp_label = competitors[0].label

    for draft in drafts:
        if draft.entity_label == comp_label:
            draft.mentioned = True
        if draft.entity_id == OWN_ENTITY_ID:
            draft.mentioned = False

    scope = page_geo_brand_scope(drafts, own_brand="Aperix", competitors=competitors)
    assert scope == ["Beta"]


def test_page_geo_brand_scope_includes_own_when_mentioned() -> None:
    subject = _subject_with_competitor()
    drafts = init_entity_signal_drafts(subject)
    competitors = competitor_entries(subject)

    for draft in drafts:
        draft.mentioned = draft.entity_kind in ("own", "competitor")

    scope = page_geo_brand_scope(drafts, own_brand="Aperix", competitors=competitors)
    assert scope == ["Aperix", "Beta"]


def test_page_geo_brand_scope_empty_when_no_response_mentions() -> None:
    subject = _subject_with_competitor()
    drafts = init_entity_signal_drafts(subject)
    competitors = competitor_entries(subject)

    scope = page_geo_brand_scope(drafts, own_brand="Aperix", competitors=competitors)
    assert scope == []


def test_page_geo_brand_scope_includes_cross_validated_other_brands() -> None:
    subject = _subject_with_competitor()
    drafts = init_entity_signal_drafts(subject)
    competitors = competitor_entries(subject)

    scope = page_geo_brand_scope(
        drafts,
        own_brand="Aperix",
        competitors=competitors,
        cross_validated_other_brands=["Stripe"],
    )
    assert scope == ["Stripe"]
