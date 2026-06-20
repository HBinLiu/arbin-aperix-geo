"""Tests for conditional response ABSA triggering."""

from __future__ import annotations

import uuid
from unittest.mock import patch

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.sampling.parse.context import build_parse_context
from aperix_geo.services.sampling.parse.analysis import run_parse_analysis
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
            urls=[],
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
            urls=[],
        )
        is True
    )


def test_response_absa_needed_true_when_citation_urls_present() -> None:
    drafts = [
        EntitySignalDraft(entity_id="own", entity_kind="own", entity_label="Aperix"),
    ]
    assert (
        response_absa_needed(
            llm_configured=True,
            text="see https://example.com/article for details",
            entity_signals=drafts,
            urls=["https://example.com/article"],
        )
        is True
    )


def test_build_parse_context_skips_absa_without_triggers() -> None:
    from unittest.mock import MagicMock

    mock_settings = MagicMock()
    mock_settings.deepseek_api_key = "sk-test"
    mock_settings.citation_response_absa_cache_ttl_s = 3600
    mock_settings.citation_text_snippet_chars = 4000
    mock_settings.citation_page_geo_llm_enabled = True
    mock_settings.citation_page_geo_cache_ttl_s = 3600
    mock_settings.citation_page_geo_batch_size = 8
    with patch("aperix_geo.services.sampling.parse.context.get_settings", return_value=mock_settings):
        ctx = build_parse_context(
            "Cloud computing trends in 2026 without brand names.",
            subject=_subject(),
            source_urls=None,
            web_search_mode="none",
            sampling_job_id=None,
        )
    assert ctx.absa_needed is False


def test_run_parse_analysis_skips_absa_call_when_not_needed() -> None:
    from unittest.mock import MagicMock

    mock_settings = MagicMock()
    mock_settings.deepseek_api_key = "sk-test"
    mock_settings.citation_response_absa_cache_ttl_s = 3600
    mock_settings.citation_text_snippet_chars = 4000
    mock_settings.citation_page_geo_llm_enabled = False
    mock_settings.citation_page_geo_cache_ttl_s = 3600
    mock_settings.citation_page_geo_batch_size = 8
    with (
        patch("aperix_geo.services.sampling.parse.context.get_settings", return_value=mock_settings),
        patch("aperix_geo.services.sampling.parse.analysis.analyze_response_absa") as absa,
        patch("aperix_geo.services.sampling.parse.analysis.resolve_citation_sources") as resolve,
    ):
        ctx = build_parse_context(
            "Industry trends only.",
            subject=_subject(),
            source_urls=None,
            web_search_mode="none",
            sampling_job_id=None,
        )
        citation, response_absa = run_parse_analysis(ctx)

    absa.assert_not_called()
    resolve.assert_not_called()
    assert citation.citation_sources == []
    assert response_absa == {}
