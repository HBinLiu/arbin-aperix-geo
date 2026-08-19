"""Tests for conditional response ABSA triggering."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.sampling.parse.analysis import enrich_parse_context
from aperix_geo.services.sampling.parse.context import extract_parse_context
from aperix_geo.services.sampling.response_absa import response_absa_needed
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft


def _subject(**kwargs) -> Subject:
    subject_id = uuid.uuid4()
    subject = Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand=kwargs.get("brand", "Aperix"),
        domain=kwargs.get("domain", "aperix.com"),
    )
    subject.competitors = kwargs.get("competitors") or [
        Competitor(
            id=uuid.uuid4(),
            subject_id=subject_id,
            brand="Beta",
            domain="beta.com",
        )
    ]
    return subject


def test_response_absa_needed_false_when_no_mentions_or_citations() -> None:
    drafts = [
        EntitySignalDraft(entity_id="own", entity_kind="own", entity_label="Aperix"),
        EntitySignalDraft(entity_id="c1", entity_kind="competitor", entity_label="Beta"),
    ]
    assert (
        response_absa_needed(
            llm_configured=True,
            text="generic industry overview without brands",
            entity_signals=drafts,
        )
        is False
    )


def test_response_absa_needed_true_when_monitored_brand_mentioned() -> None:
    drafts = [
        EntitySignalDraft(
            entity_id="own",
            entity_kind="own",
            entity_label="Aperix",
            mentioned=True,
            mention_count=1,
        ),
    ]
    assert (
        response_absa_needed(
            llm_configured=True,
            text="Aperix is mentioned here",
            entity_signals=drafts,
        )
        is True
    )


def test_response_absa_needed_false_when_only_citation_urls_present() -> None:
    drafts = [
        EntitySignalDraft(entity_id="own", entity_kind="own", entity_label="Aperix"),
    ]
    assert (
        response_absa_needed(
            llm_configured=True,
            text="see https://example.com/article for details",
            entity_signals=drafts,
        )
        is False
    )


def test_extract_parse_context_skips_absa_without_triggers() -> None:
    mock_settings = MagicMock()
    mock_settings.deepseek_api_key = "sk-test"
    mock_settings.citation_response_absa_cache_ttl_s = 3600
    mock_settings.citation_response_mention_discovery_enabled = True
    mock_settings.citation_response_mention_discovery_cache_ttl_s = 3600
    mock_settings.citation_text_snippet_chars = 4000
    with patch("aperix_geo.services.sampling.parse.context.get_settings", return_value=mock_settings):
        ctx = extract_parse_context(
            "Cloud computing trends in 2026 without brand names.",
            subject=_subject(),
            source_urls=None,
            web_search_mode="none",
            sampling_job_id=None,
        )
    assert ctx.absa_needed is False


def test_enrich_parse_context_skips_absa_call_when_not_needed() -> None:
    mock_settings = MagicMock()
    mock_settings.deepseek_api_key = "sk-test"
    mock_settings.citation_response_absa_cache_ttl_s = 3600
    mock_settings.citation_response_mention_discovery_enabled = True
    mock_settings.citation_response_mention_discovery_cache_ttl_s = 3600
    mock_settings.citation_text_snippet_chars = 4000
    with (
        patch("aperix_geo.services.sampling.parse.context.get_settings", return_value=mock_settings),
        patch("aperix_geo.services.sampling.parse.analysis.analyze_response_absa") as absa,
        patch("aperix_geo.services.sampling.parse.analysis.fetch_citation_pages_for_urls") as fetch_pages,
    ):
        ctx = extract_parse_context(
            "Industry trends only.",
            subject=_subject(),
            source_urls=None,
            web_search_mode="none",
            sampling_job_id=None,
        )
        enrichment = enrich_parse_context(ctx)

    absa.assert_not_called()
    fetch_pages.assert_not_called()
    assert enrichment.citation.citation_sources == []
    assert enrichment.response_absa == {}
