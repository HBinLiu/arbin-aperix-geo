"""Tests for parse three-phase pipeline wiring."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.sampling.citation import empty_citation_document
from aperix_geo.services.sampling.parse.pipeline import run_parse_pipeline
from aperix_geo.services.sampling.parse.types import ParseEnrichment, ParseMergeResult
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft


def _subject() -> Subject:
    return Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        domain="aperix.com",
    )


@patch("aperix_geo.services.sampling.parse.pipeline.merge_parse_results")
@patch("aperix_geo.services.sampling.parse.pipeline.enrich_parse_context")
@patch("aperix_geo.services.sampling.parse.pipeline.extract_parse_context")
def test_run_parse_pipeline_wires_three_phases(
    mock_extract: MagicMock,
    mock_enrich: MagicMock,
    mock_merge: MagicMock,
) -> None:
    ctx = MagicMock()
    ctx.urls = ["https://aperix.com/docs"]
    ctx.url_hosts = ["aperix.com"]
    ctx.web_search_mode = "none"
    ctx.source_urls = None
    ctx.own_brand = "Aperix"
    mock_extract.return_value = ctx

    citation = empty_citation_document()
    enrichment = ParseEnrichment(citation=citation, response_absa={"analysis_source": "llm"})
    mock_enrich.return_value = enrichment

    draft = EntitySignalDraft(entity_id="own", entity_kind="own", entity_label="Aperix")
    mock_merge.return_value = ParseMergeResult(
        entity_signals=[draft],
        sentiment_source="llm",
        response_absa=enrichment.response_absa,
    )

    subject = _subject()
    parsed = run_parse_pipeline("推荐 Aperix", subject=subject)

    mock_extract.assert_called_once()
    mock_enrich.assert_called_once_with(ctx, fetch_pages=True)
    mock_merge.assert_called_once_with(ctx, enrichment=enrichment)
    assert parsed.own_brand == "Aperix"
    assert parsed.sentiment_source == "llm"
    assert parsed.entity_signals == [draft]
