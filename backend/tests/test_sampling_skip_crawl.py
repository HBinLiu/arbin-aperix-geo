"""Tests for B1: skip crawl when LLM output has no citation URLs."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from aperix_geo.db.models import LLMResponse, LLMResponseStatus
from aperix_geo.services.providers.result import SamplingChatResult


def test_persist_llm_result_skips_crawl_without_urls() -> None:
    from aperix_geo.services.sampling.persist.response import persist_llm_result

    row = LLMResponse(
        id=uuid4(),
        sampling_job_id=uuid4(),
        prompt_id=uuid4(),
        platform="openai",
        status=LLMResponseStatus.pending,
    )
    result = SamplingChatResult(
        text="no links here",
        usage={},
        latency_ms=100,
    )

    persist_llm_result(MagicMock(), row=row, result=result)

    assert row.status == LLMResponseStatus.crawl_ready
    assert row.share_url == ""
    assert row.parsed.get("sampling_source") == "api"


def test_persist_llm_result_keeps_llm_ready_with_urls() -> None:
    from aperix_geo.services.sampling.persist.response import persist_llm_result

    row = LLMResponse(
        id=uuid4(),
        sampling_job_id=uuid4(),
        prompt_id=uuid4(),
        platform="openai",
        status=LLMResponseStatus.pending,
    )
    result = SamplingChatResult(
        text="see https://wise.com/page",
        usage={},
        latency_ms=100,
        source_urls=("https://wise.com/page",),
    )

    persist_llm_result(MagicMock(), row=row, result=result)

    assert row.status == LLMResponseStatus.llm_ready


def test_persist_llm_result_crawl_sets_share_url_and_source() -> None:
    from aperix_geo.services.sampling.persist.response import persist_llm_result

    row = LLMResponse(
        id=uuid4(),
        sampling_job_id=uuid4(),
        prompt_id=uuid4(),
        platform="doubao",
        status=LLMResponseStatus.pending,
        share_url="",
    )
    result = SamplingChatResult(
        text="crawled reply",
        usage={},
        latency_ms=2000,
        web_search_mode="doubao_web_crawl",
        search_queries=("关键词A",),
        share_url="https://www.doubao.com/share/xyz",
    )

    persist_llm_result(MagicMock(), row=row, result=result)

    assert row.share_url == "https://www.doubao.com/share/xyz"
    assert row.parsed.get("sampling_source") == "crawl"
    assert row.parsed.get("web_search_mode") == "doubao_web_crawl"
