"""Build citation row dicts and persist them for one LLM response."""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from aperix_geo.db.models import CitationDomain, CitationUrl
from aperix_geo.services.sampling.parsed import ParsedSamplingResult
from aperix_geo.utils.coerce import safe_int
from aperix_geo.utils.net import filter_citation_urls, host_from, is_citation_host, registrable_from


def _headings_text(headings: Any) -> str:
    if isinstance(headings, list):
        return " | ".join(str(h).strip() for h in headings if str(h).strip())
    return str(headings or "").strip()


def citations_from_parsed(parsed: dict[str, Any] | ParsedSamplingResult) -> list[dict[str, Any]]:
    """Build citation URL row dicts from parse_llm_output JSON."""
    data = parsed.to_dict() if isinstance(parsed, ParsedSamplingResult) else parsed
    source_map: dict[str, dict[str, Any]] = {}
    for item in data.get("citation_sources") or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if url:
            source_map[url] = item

    api_urls = {str(u).strip() for u in (data.get("source_urls_from_api") or []) if str(u).strip()}

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for url in filter_citation_urls(list(data.get("urls") or [])):
        key = str(url).strip()
        if not key or key in seen:
            continue
        host = host_from(key)
        domain = registrable_from(key)
        if not domain or not is_citation_host(host):
            continue
        seen.add(key)
        src = source_map.get(key, {})
        page_title = str(src.get("page_title") or "").strip()
        llm_analysis = src.get("llm_analysis") if isinstance(src.get("llm_analysis"), dict) else {}
        rows.append(
            {
                "domain": domain[:255],
                "url": key,
                "page_title": page_title[:500],
                "http_status": safe_int(src, "http_status", 0),
                "description": str(src.get("description") or "")[:8000],
                "headings": _headings_text(src.get("headings"))[:4000],
                "has_table": bool(src.get("has_table")),
                "has_code_block": bool(src.get("has_code_block")),
                "text_snippet": str(src.get("text_snippet") or "")[:20000],
                "llm_analysis": llm_analysis,
                "fetch_ok": bool(src.get("fetch_ok")),
                "from_api": key in api_urls,
            }
        )
    return rows


def domain_counts_from_url_rows(url_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in url_rows:
        domain = str(row.get("domain") or "").strip()
        if domain:
            counts[domain] += 1
    return dict(counts)


def replace_citations_for_response(
    db: Session,
    *,
    response_id: UUID,
    prompt_id: UUID,
    parsed: dict[str, Any] | ParsedSamplingResult,
) -> int:
    """Replace citation URL/domain rows for one LLM response; returns URL count."""
    db.execute(
        delete(CitationUrl).where(CitationUrl.response_id == response_id)
    )
    db.execute(
        delete(CitationDomain).where(
            CitationDomain.response_id == response_id
        )
    )
    # Apply deletes before ORM inserts so (response_id, domain) unique rows are cleared first.
    db.flush()

    url_rows = citations_from_parsed(parsed)
    for row in url_rows:
        db.add(
            CitationUrl(
                response_id=response_id,
                prompt_id=prompt_id,
                url=row["url"],
                page_title=row["page_title"],
                http_status=row["http_status"],
                description=row["description"],
                headings=row["headings"],
                has_table=row["has_table"],
                has_code_block=row["has_code_block"],
                text_snippet=row["text_snippet"],
                llm_analysis=row["llm_analysis"],
                fetch_ok=row["fetch_ok"],
                from_api=row["from_api"],
            )
        )

    for domain, cite_count in domain_counts_from_url_rows(url_rows).items():
        db.add(
            CitationDomain(
                response_id=response_id,
                prompt_id=prompt_id,
                domain=domain,
                cite_count=cite_count,
            )
        )

    return len(url_rows)
