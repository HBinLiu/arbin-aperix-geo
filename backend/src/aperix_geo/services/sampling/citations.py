"""Persist and aggregate LLM response citation sources."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import CitationDomain, CitationUrl, LLMResponse, Subject
from aperix_geo.services.sampling.citation_analysis import page_mentioned_brand_names
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.utils.url import filter_citation_urls, hostname_from_url, is_placeholder_citation_host


def _competitor_label(*, brand: str = "", domain: str = "") -> str:
    normalized = registrable_domain(domain.strip()) if domain.strip() else ""
    if normalized:
        return normalized
    return brand.strip()


def _competitor_domain_map(subject: Subject | None) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if subject is None:
        return mapping
    for competitor in subject.competitors or []:
        brand = (competitor.brand or "").strip()
        domain = (competitor.domain or "").strip()
        label = _competitor_label(brand=brand, domain=domain)
        if label and domain:
            mapping[label] = registrable_domain(domain) or domain
        if brand:
            mapping[brand] = registrable_domain(domain) or domain
    return mapping


def _mode_nonempty(values: list[str]) -> str:
    cleaned = [value.strip() for value in values if value and value.strip()]
    if not cleaned:
        return ""
    return Counter(cleaned).most_common(1)[0][0]


def _headings_text(headings: Any) -> str:
    if isinstance(headings, list):
        return " | ".join(str(h).strip() for h in headings if str(h).strip())
    return str(headings or "").strip()


def citations_from_parsed(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    """Build citation URL row dicts from parse_llm_output JSON."""
    source_map: dict[str, dict[str, Any]] = {}
    for item in parsed.get("citation_sources") or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        if url:
            source_map[url] = item

    api_urls = {str(u).strip() for u in (parsed.get("source_urls_from_api") or []) if str(u).strip()}

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for url in filter_citation_urls(list(parsed.get("urls") or [])):
        key = str(url).strip()
        if not key or key in seen:
            continue
        domain = (hostname_from_url(key) or "").strip().lower()
        if not domain or is_placeholder_citation_host(domain):
            continue
        seen.add(key)
        src = source_map.get(key, {})
        page_title = str(src.get("page_title") or "").strip()
        url_type = str(src.get("url_type") or "").strip()
        domain_type = str(src.get("domain_type") or "").strip()
        llm_analysis = src.get("llm_analysis") if isinstance(src.get("llm_analysis"), dict) else {}
        rows.append(
            {
                "domain": domain[:255],
                "url": key,
                "page_title": page_title[:500],
                "domain_type": domain_type[:128],
                "url_type": url_type[:128],
                "http_status": src.get("http_status"),
                "description": str(src.get("description") or "")[:8000],
                "headings": _headings_text(src.get("headings"))[:4000],
                "has_table": src.get("has_table"),
                "has_code_block": src.get("has_code_block"),
                "text_snippet": str(src.get("text_snippet") or "")[:20000],
                "llm_analysis": llm_analysis,
                "fetch_ok": src.get("fetch_ok"),
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


def domain_types_from_url_rows(url_rows: list[dict[str, Any]]) -> dict[str, str]:
    types: dict[str, list[str]] = defaultdict(list)
    for row in url_rows:
        domain = str(row.get("domain") or "").strip()
        domain_type = str(row.get("domain_type") or "").strip()
        if domain and domain_type:
            types[domain].append(domain_type)
    return {domain: _mode_nonempty(values) for domain, values in types.items()}


def replace_citations_for_response(
    db: Session,
    *,
    response_id: UUID,
    prompt_id: UUID,
    parsed: dict[str, Any],
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

    url_rows = citations_from_parsed(parsed)
    for row in url_rows:
        db.add(
            CitationUrl(
                response_id=response_id,
                prompt_id=prompt_id,
                url=row["url"],
                page_title=row["page_title"],
                domain_type=row["domain_type"],
                http_status=row["http_status"],
                description=row["description"],
                headings=row["headings"],
                has_table=row["has_table"],
                has_code_block=row["has_code_block"],
                text_snippet=row["text_snippet"],
                llm_analysis=row["llm_analysis"],
                fetch_ok=row["fetch_ok"],
                from_api=row["from_api"],
                url_type=row["url_type"],
            )
        )

    domain_types = domain_types_from_url_rows(url_rows)
    for domain, cite_count in domain_counts_from_url_rows(url_rows).items():
        db.add(
            CitationDomain(
                response_id=response_id,
                prompt_id=prompt_id,
                domain=domain,
                cite_count=cite_count,
                domain_type=domain_types.get(domain, ""),
            )
        )

    return len(url_rows)


def _aggregate_domains_from_parsed(rows: list[LLMResponse]) -> dict[str, int]:
    host_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        for h in (r.parsed or {}).get("url_hosts") or []:
            if h and not is_placeholder_citation_host(str(h)):
                host_counts[str(h)] += 1
    return dict(host_counts)


def _aggregate_urls_from_parsed(rows: list[LLMResponse]) -> dict[str, int]:
    url_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        for url in filter_citation_urls(list((r.parsed or {}).get("urls") or [])):
            if url:
                url_counts[str(url)] += 1
    return dict(url_counts)


def _mentioned_brands_for_records(
    records: list[CitationUrl],
    *,
    competitor_domains: dict[str, str],
) -> list[dict[str, str | None]]:
    labels: list[str] = []
    seen: set[str] = set()
    for record in records:
        for name in page_mentioned_brand_names(record.llm_analysis if isinstance(record.llm_analysis, dict) else {}):
            if name in seen:
                continue
            seen.add(name)
            labels.append(name)
    return [{"label": label, "domain": competitor_domains.get(label)} for label in labels]


def _aggregate_url_row(
    url: str,
    records: list[CitationUrl],
    *,
    total: int,
    competitor_domains: dict[str, str],
) -> dict[str, Any]:
    count = len(records)
    host = (hostname_from_url(url) or "").strip().lower()
    page_title = _mode_nonempty([record.page_title for record in records])
    url_type = _mode_nonempty([record.url_type for record in records])
    domain_type = _mode_nonempty([record.domain_type for record in records])
    if not page_title:
        page_title = records[0].page_title if records else ""

    mentioned_brands = _mentioned_brands_for_records(records, competitor_domains=competitor_domains)
    has_brand_analysis = any(
        isinstance(record.llm_analysis, dict)
        and (
            "page_mentioned_brands" in record.llm_analysis
            or record.llm_analysis.get("analysis_source") in ("llm", "heuristic")
        )
        for record in records
    )

    return {
        "url": url,
        "host": host,
        "title": page_title or url,
        "url_type": url_type or None,
        "domain_type": domain_type or None,
        "count": count,
        "citation_rate": round(count / total, 4) if total else 0,
        "has_brand_analysis": has_brand_analysis,
        "mentioned_brands": mentioned_brands,
    }


def aggregate_citation_domains(
    db: Session,
    rows: list[LLMResponse],
) -> list[dict[str, Any]]:
    """Domain-level citation counts for a response window."""
    if not rows:
        return []
    total = len(rows)
    response_ids = [r.id for r in rows]
    stmt = (
        select(
            CitationDomain.domain,
            func.sum(CitationDomain.cite_count),
            func.max(CitationDomain.domain_type),
        )
        .where(CitationDomain.response_id.in_(response_ids))
        .group_by(CitationDomain.domain)
    )
    db_rows = db.execute(stmt).all()
    if db_rows:
        host_counts = {domain: int(count) for domain, count, _ in db_rows if domain}
        domain_types = {domain: str(domain_type or "").strip() for domain, _, domain_type in db_rows if domain}
    else:
        host_counts = _aggregate_domains_from_parsed(rows)
        domain_types = {}
    return sorted(
        [
            {
                "host": host,
                "count": count,
                "citation_rate": round(count / total, 4) if total else 0,
                "domain_type": domain_types.get(host) or None,
            }
            for host, count in host_counts.items()
        ],
        key=lambda row: -row["count"],
    )


def aggregate_citation_urls(
    db: Session,
    rows: list[LLMResponse],
    *,
    subject: Subject | None = None,
) -> list[dict[str, Any]]:
    """URL-level citation counts and source-page metadata for a response window."""
    if not rows:
        return []
    total = len(rows)
    response_ids = [r.id for r in rows]
    competitor_domains = _competitor_domain_map(subject)

    records = db.execute(
        select(CitationUrl).where(CitationUrl.response_id.in_(response_ids))
    ).scalars().all()

    grouped: dict[str, list[CitationUrl]] = defaultdict(list)
    for record in records:
        grouped[record.url].append(record)

    if grouped:
        return sorted(
            [
                _aggregate_url_row(
                    url,
                    grouped[url],
                    total=total,
                    competitor_domains=competitor_domains,
                )
                for url in grouped
            ],
            key=lambda row: -row["count"],
        )

    url_counts = _aggregate_urls_from_parsed(rows)
    return sorted(
        [
            {
                "url": url,
                "host": (hostname_from_url(url) or "").strip().lower(),
                "title": url.rsplit("/", 1)[-1] or url,
                "url_type": None,
                "domain_type": None,
                "count": count,
                "citation_rate": round(count / total, 4) if total else 0,
                "has_brand_analysis": False,
                "mentioned_brands": [],
            }
            for url, count in url_counts.items()
        ],
        key=lambda row: -row["count"],
    )
