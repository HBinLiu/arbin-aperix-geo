"""Tests for single cross-validate filter during parse analysis."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.sampling.parse.analysis import run_parse_analysis
from aperix_geo.services.sampling.parse.context import build_parse_context


def _subject() -> Subject:
    subject_id = uuid.uuid4()
    subject = Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        domain="aperix.com",
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


def test_parse_analysis_filters_open_brands_once() -> None:
    mock_settings = MagicMock()
    mock_settings.deepseek_api_key = "sk-test"
    mock_settings.citation_response_absa_cache_ttl_s = 3600
    mock_settings.citation_text_snippet_chars = 4000
    mock_settings.citation_page_geo_llm_enabled = False
    mock_settings.citation_page_geo_cache_ttl_s = 3600
    mock_settings.citation_page_geo_batch_size = 8

    absa = {
        "analysis_source": "llm",
        "brands_sentiment_absa": {"Aperix": {"mentioned": True, "score": 80, "evidence": "Aperix"}},
        "other_brands_sentiment_absa": {
            "Stripe": {"mentioned": True, "score": 75, "evidence": "Stripe"},
        },
    }
    filtered = {
        **absa,
        "other_brands_sentiment_absa": {
            "Stripe": {"mentioned": True, "score": 75, "evidence": "Stripe"},
        },
    }

    db = MagicMock()
    with (
        patch("aperix_geo.services.sampling.parse.context.get_settings", return_value=mock_settings),
        patch(
            "aperix_geo.services.sampling.parse.analysis.analyze_response_absa",
            return_value=absa,
        ) as analyze,
        patch(
            "aperix_geo.services.sampling.parse.analysis.filter_open_brands_in_response_absa",
            return_value=filtered,
        ) as filter_once,
            patch(
                "aperix_geo.services.sampling.parse.analysis.fetch_citation_pages_for_urls",
                return_value=[],
            ),
            patch(
                "aperix_geo.services.sampling.parse.analysis.build_citation_document",
                return_value=MagicMock(citation_urls_own=[], citation_sources=[]),
            ) as build_doc,
    ):
        ctx = build_parse_context(
            "推荐 Aperix 与 Stripe，详见 https://aperix.com/docs",
            subject=_subject(),
            source_urls=None,
            web_search_mode="none",
            sampling_job_id=None,
            db=db,
        )
        _, response_absa = run_parse_analysis(ctx)

    analyze.assert_called_once()
    filter_once.assert_called_once()
    build_doc.assert_called_once()
    assert build_doc.call_args.kwargs["cross_validated_other_brands"] == ["Stripe"]
    assert response_absa == filtered
