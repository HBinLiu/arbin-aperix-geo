"""Persist parsed sampling results to DB stores."""

from __future__ import annotations

from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, LLMResponseStatus, Subject
from aperix_geo.services.providers.result import SamplingChatResult
from aperix_geo.services.sampling.fanout import build_search_query_events
from aperix_geo.services.sampling.parse.context import extract_citation_urls
from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from aperix_geo.services.sampling.persist.artifacts import refresh_parsed_artifacts
from aperix_geo.utils.sanitize import sanitize_json_value, sanitize_text


def persist_llm_result(
    db: Session,
    *,
    row: LLMResponse,
    result: SamplingChatResult,
) -> None:
    """Store platform LLM output; parse/citation runs in a follow-up task."""
    queries = list(result.search_queries)
    sampling_source = (
        "crawl" if str(result.web_search_mode or "") == "doubao_web_crawl" else "api"
    )
    row.raw_text = sanitize_text(result.text)
    row.share_url = sanitize_text(result.share_url)
    row.parsed = sanitize_json_value(
        {
            "source_urls_from_api": list(result.source_urls),
            "web_search_mode": result.web_search_mode,
            "search_queries_from_api": queries,
            "search_query_events": build_search_query_events(queries, platform=str(row.platform or "")),
            "sampling_source": sampling_source,
        }
    )
    row.usage = sanitize_json_value(result.usage or {})
    row.latency_ms = result.latency_ms
    urls, _ = extract_citation_urls(result.text, list(result.source_urls))
    if not urls:
        row.status = LLMResponseStatus.crawl_ready
    else:
        row.status = LLMResponseStatus.llm_ready
    row.error_text = ""
    if queries:
        from aperix_geo.services.sampling.prompt_fanouts import upsert_prompt_fanouts_for_response

        upsert_prompt_fanouts_for_response(
            db,
            prompt_id=row.prompt_id,
            platform=str(row.platform or ""),
            queries=queries,
            seen_at=row.created_at,
        )


def persist_successful_response(
    db: Session,
    *,
    row: LLMResponse,
    result: SamplingChatResult,
    parsed: ParsedSamplingResult,
    subject: Subject,
) -> None:
    """Write document JSONB and derived citation/signal rows (caller commits)."""
    prior = row.parsed if isinstance(row.parsed, dict) else {}
    sampling_source = str(prior.get("sampling_source") or "").strip()
    if not sampling_source:
        sampling_source = (
            "crawl" if str(result.web_search_mode or "") == "doubao_web_crawl" else "api"
        )
    # share_url is a first-class column — never clear it on re-parse.
    row.raw_text = sanitize_text(result.text)
    payload = parsed.to_dict()
    payload["sampling_source"] = sampling_source
    row.parsed = sanitize_json_value(payload)
    row.usage = sanitize_json_value(result.usage or {})
    row.latency_ms = result.latency_ms
    row.status = LLMResponseStatus.success
    row.error_text = ""
    refresh_parsed_artifacts(db, row=row, subject=subject, parsed=parsed)
