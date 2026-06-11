"""Tests for citation → entity signal draft mapping."""

from __future__ import annotations

import uuid

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.analysis.entity import OWN_ENTITY_ID
from aperix_geo.services.sampling.citation.apply import apply_citation_to_drafts, reset_citation_drafts
from aperix_geo.services.sampling.citation.document import CitationDocument
from aperix_geo.services.sampling.mentions import competitor_entries
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft, init_entity_signal_drafts


def _subject() -> Subject:
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
            brand="Beta",
            domain="beta.com",
        )
    ]
    return subject


def test_apply_citation_to_drafts_own_link_and_cited_on_source() -> None:
    subject = _subject()
    drafts = init_entity_signal_drafts(subject)
    competitors = competitor_entries(subject)
    citation = CitationDocument(
        citation_urls_own=["https://aperix.com/page"],
        citation_sources=[
            {
                "url": "https://aperix.com/page",
                "target": "own",
                "llm_analysis": {
                    "page_mentioned_brands": ["Aperix"],
                    "analysis_source": "llm",
                },
            }
        ],
    )
    apply_citation_to_drafts(
        drafts,
        citation,
        own_brand="Aperix",
        own_names=["Aperix", "aperix.com"],
        competitors=competitors,
    )
    own = next(d for d in drafts if d.entity_id == OWN_ENTITY_ID)
    assert own.has_domain_link is True
    assert own.cited_on_source is True


def test_apply_citation_to_drafts_competitor_domain_link() -> None:
    subject = _subject()
    drafts = init_entity_signal_drafts(subject)
    competitors = competitor_entries(subject)
    comp_label = competitors[0].label
    citation = CitationDocument(
        citation_urls_own=[],
        citation_sources=[
            {
                "url": "https://beta.com/post",
                "target": comp_label,
                "llm_analysis": {"page_mentioned_brands": [], "analysis_source": "heuristic"},
            }
        ],
    )
    apply_citation_to_drafts(
        drafts,
        citation,
        own_brand="Aperix",
        own_names=["Aperix"],
        competitors=competitors,
    )
    comp = next(d for d in drafts if d.entity_kind == "competitor")
    assert comp.has_domain_link is True
    assert comp.cited_on_source is False


def test_apply_citation_to_drafts_competitor_cited_on_any_page() -> None:
    subject = _subject()
    drafts = init_entity_signal_drafts(subject)
    competitors = competitor_entries(subject)
    citation = CitationDocument(
        citation_urls_own=[],
        citation_sources=[
            {
                "url": "https://news.example.com/review",
                "target": "",
                "llm_analysis": {
                    "page_mentioned_brands": ["Beta"],
                    "analysis_source": "llm",
                },
            }
        ],
    )
    apply_citation_to_drafts(
        drafts,
        citation,
        own_brand="Aperix",
        own_names=["Aperix"],
        competitors=competitors,
    )
    comp = next(d for d in drafts if d.entity_kind == "competitor")
    assert comp.cited_on_source is True


def test_reset_citation_drafts() -> None:
    drafts = [
        EntitySignalDraft(
            entity_id=OWN_ENTITY_ID,
            entity_kind="own",
            entity_label="aperix.com",
            has_domain_link=True,
            cited_on_source=True,
        )
    ]
    reset_citation_drafts(drafts)
    assert drafts[0].has_domain_link is False
    assert drafts[0].cited_on_source is False
