"""Backlink opportunity analysis."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import CitationDomain, CitationUrl, EntityKind, LLMResponse, LLMResponseSignal, Prompt, Subject
from aperix_geo.services.analysis.entity import own_entity
from aperix_geo.utils.net import citation_registrable_key, registrable_from


def citation_root_for_subject(subject: Subject) -> str | None:
    from aperix_geo.services.sampling.citation import citation_root

    return citation_root(subject)


def backlink_priority(prompt_count: int, chat_count: int) -> str:
    if prompt_count >= 5 or chat_count >= 8:
        return "high"
    if prompt_count >= 2 or chat_count >= 3:
        return "medium"
    return "low"


_BACKLINK_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _backlink_row_rank_key(row: dict[str, Any]) -> tuple[int, int, int, str]:
    return (
        _BACKLINK_PRIORITY_ORDER.get(row["priority"], 9),
        -row["chat_count"],
        -row["prompt_count"],
        row["domain"],
    )


def _filter_backlink_by_search(items: list[dict[str, Any]], search: str | None) -> list[dict[str, Any]]:
    query = (search or "").strip().lower()
    if not query:
        return items
    return [item for item in items if query in item["domain"].lower()]


def _sort_backlink_items(
    items: list[dict[str, Any]],
    *,
    sort_by: str | None,
    order: str,
) -> list[dict[str, Any]]:
    if not sort_by:
        return sorted(items, key=_backlink_row_rank_key)

    reverse = order == "desc"
    if sort_by == "priority":
        return sorted(
            items,
            key=lambda row: (_BACKLINK_PRIORITY_ORDER.get(row["priority"], 9), row["domain"]),
            reverse=reverse,
        )
    if sort_by == "prompt_count":
        return sorted(items, key=lambda row: row["prompt_count"], reverse=reverse)
    if sort_by == "chat_count":
        return sorted(items, key=lambda row: row["chat_count"], reverse=reverse)
    if sort_by == "citation_count":
        return sorted(items, key=lambda row: row["citation_count"], reverse=reverse)
    return sorted(items, key=_backlink_row_rank_key)


def _backlink_search_needle(search: str | None) -> str | None:
    text = (search or "").strip().lower()
    return text or None


def _backlink_ilike_pattern(needle: str) -> str:
    escaped = needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _backlink_priority_rank_expr(prompt_count_col, chat_count_col):
    return case(
        (or_(prompt_count_col >= 5, chat_count_col >= 8), 0),
        (or_(prompt_count_col >= 2, chat_count_col >= 3), 1),
        else_=2,
    )


def _backlink_grouped_subquery(
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
    own_root: str | None,
):
    eligible = _backlink_eligible_response_ids_stmt(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    ).subquery()
    return (
        select(
            CitationDomain.domain.label("domain"),
            func.sum(CitationDomain.cite_count).label("citation_count"),
            func.count(func.distinct(CitationDomain.response_id)).label("chat_count"),
            func.count(func.distinct(CitationDomain.prompt_id)).label("prompt_count"),
        )
        .where(
            CitationDomain.response_id.in_(select(eligible.c.id)),
            _exclude_own_domain(CitationDomain.domain, own_root),
        )
        .group_by(CitationDomain.domain)
    ).subquery()


def _backlink_sql_order_clauses(grouped, priority_rank, *, sort_by: str | None, order: str):
    domain_col = grouped.c.domain
    if not sort_by:
        return (
            priority_rank.asc(),
            grouped.c.chat_count.desc(),
            grouped.c.prompt_count.desc(),
            domain_col.asc(),
        )
    reverse = order == "desc"
    if sort_by == "priority":
        priority_order = priority_rank.desc() if reverse else priority_rank.asc()
        return (priority_order, domain_col.asc())
    if sort_by == "prompt_count":
        col = grouped.c.prompt_count.desc() if reverse else grouped.c.prompt_count.asc()
        return (col, domain_col.asc())
    if sort_by == "chat_count":
        col = grouped.c.chat_count.desc() if reverse else grouped.c.chat_count.asc()
        return (col, domain_col.asc())
    if sort_by == "citation_count":
        col = grouped.c.citation_count.desc() if reverse else grouped.c.citation_count.asc()
        return (col, domain_col.asc())
    return (
        priority_rank.asc(),
        grouped.c.chat_count.desc(),
        grouped.c.prompt_count.desc(),
        domain_col.asc(),
    )


def _backlink_row_from_sql(domain, citation_count, chat_count, prompt_count) -> dict[str, Any] | None:
    domain_key = str(domain or "").strip().lower()
    if not domain_key:
        return None
    chat = int(chat_count or 0)
    if chat <= 0:
        return None
    prompts = int(prompt_count or 0)
    return {
        "id": domain_key,
        "domain": domain_key,
        "platforms": [],
        "priority": backlink_priority(prompts, chat),
        "citation_count": int(citation_count or 0),
        "prompt_count": prompts,
        "chat_count": chat,
    }


@dataclass(frozen=True)
class _BacklinkDomainContext:
    domain: str
    citation_count: int
    chat_count: int
    prompt_count: int
    platforms: list[str]


def _backlink_window_subquery(
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
):
    return _backlink_eligible_response_ids_stmt(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    ).subquery()


def _backlink_domain_filter(domain: str, eligible_subq) -> Any:
    return and_(
        CitationDomain.response_id.in_(select(eligible_subq.c.id)),
        CitationDomain.domain == domain,
    )


def _backlink_domain_response_ids_stmt(
    *,
    subject_id: UUID,
    domain: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
):
    eligible = _backlink_window_subquery(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    return select(CitationDomain.response_id).where(_backlink_domain_filter(domain, eligible)).distinct()


def _exclude_own_domain(domain_column, own_root: str | None):
    if not own_root:
        return True
    root = registrable_from(own_root) or own_root.strip().lower()
    if not root:
        return True
    return domain_column != root


def _backlink_eligible_response_ids_stmt(
    *,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
):
    from aperix_geo.services.analysis._query import response_ids_in_window_stmt

    own_kind = EntityKind.own.value
    cited_on_source_ids = (
        select(LLMResponseSignal.response_id)
        .where(
            LLMResponseSignal.subject_id == subject_id,
            LLMResponseSignal.entity_kind == own_kind,
            LLMResponseSignal.cited_on_source.is_(True),
        )
        .distinct()
    )
    window = response_ids_in_window_stmt(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=None,
    )
    return window.where(LLMResponse.id.not_in(cited_on_source_ids))


class _BacklinkDomainPageQuery:
    """Patchable domain page query (tests assign to `.override`)."""

    override: Callable[..., list[dict[str, Any]]] | None = None

    def __call__(
        self,
        db: Session,
        *,
        subject: Subject,
        dt_from: datetime,
        dt_to: datetime,
        platform: list[str] | None = None,
        topic_id: list[UUID] | None = None,
        search: str | None = None,
        sort_by: str | None = None,
        order: str = "asc",
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict[str, Any]], int]:
        if self.override is not None:
            all_items = self.override(
                db,
                subject=subject,
                dt_from=dt_from,
                dt_to=dt_to,
                platform=platform,
                topic_id=topic_id,
            )
            filtered = _filter_backlink_by_search(all_items, search)
            sorted_items = _sort_backlink_items(filtered, sort_by=sort_by, order=order)
            safe_page = max(1, page)
            safe_page_size = max(1, page_size)
            total = len(sorted_items)
            start = (safe_page - 1) * safe_page_size
            return sorted_items[start : start + safe_page_size], total
        return self._load_sql(
            db,
            subject=subject,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            search=search,
            sort_by=sort_by,
            order=order,
            page=page,
            page_size=page_size,
        )

    @staticmethod
    def _load_sql(
        db: Session,
        *,
        subject: Subject,
        dt_from: datetime,
        dt_to: datetime,
        platform: list[str] | None = None,
        topic_id: list[UUID] | None = None,
        search: str | None = None,
        sort_by: str | None = None,
        order: str = "asc",
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict[str, Any]], int]:
        safe_page = max(1, page)
        safe_page_size = max(1, page_size)
        own_root = citation_root_for_subject(subject)
        grouped = _backlink_grouped_subquery(
            subject_id=subject.id,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
            own_root=own_root,
        )
        filters = [grouped.c.chat_count > 0]
        search_needle = _backlink_search_needle(search)
        if search_needle:
            filters.append(grouped.c.domain.ilike(_backlink_ilike_pattern(search_needle)))

        filtered = select(grouped).where(*filters).subquery()
        total = int(db.scalar(select(func.count()).select_from(filtered)) or 0)
        if total == 0:
            return [], 0

        priority_rank = _backlink_priority_rank_expr(filtered.c.prompt_count, filtered.c.chat_count)
        order_clauses = _backlink_sql_order_clauses(
            filtered, priority_rank, sort_by=sort_by, order=order
        )
        offset = (safe_page - 1) * safe_page_size
        rows = db.execute(
            select(
                filtered.c.domain,
                filtered.c.citation_count,
                filtered.c.chat_count,
                filtered.c.prompt_count,
            )
            .order_by(*order_clauses)
            .offset(offset)
            .limit(safe_page_size)
        ).all()

        items: list[dict[str, Any]] = []
        for domain, citation_count, chat_count, prompt_count in rows:
            row = _backlink_row_from_sql(domain, citation_count, chat_count, prompt_count)
            if row is not None:
                items.append(row)
        return items, total


_query_backlink_domain_page = _BacklinkDomainPageQuery()
_query_backlink_domain_stats = _query_backlink_domain_page


def _attach_backlink_platforms(
    db: Session,
    *,
    items: list[dict[str, Any]],
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
) -> None:
    if not items:
        return
    page_domains = [item["domain"] for item in items]
    eligible = _backlink_eligible_response_ids_stmt(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    ).subquery()
    platform_rows = db.execute(
        select(CitationDomain.domain, LLMResponse.platform)
        .join(LLMResponse, CitationDomain.response_id == LLMResponse.id)
        .where(
            CitationDomain.response_id.in_(select(eligible.c.id)),
            CitationDomain.domain.in_(page_domains),
        )
    ).all()
    platforms_by_domain: dict[str, set[str]] = defaultdict(set)
    for domain, platform_value in platform_rows:
        domain_key = str(domain or "").strip().lower()
        if domain_key and platform_value:
            platforms_by_domain[domain_key].add(str(platform_value))
    for item in items:
        item["platforms"] = sorted(platforms_by_domain.get(item["domain"], set()))


class _BacklinkDomainContextQuery:
    """Patchable single-domain context query (tests assign to `.override`)."""

    override: Callable[..., _BacklinkDomainContext | None] | None = None

    def __call__(
        self,
        db: Session,
        *,
        subject: Subject,
        domain: str,
        dt_from: datetime,
        dt_to: datetime,
        platform: list[str] | None = None,
        topic_id: list[UUID] | None = None,
    ) -> _BacklinkDomainContext | None:
        if self.override is not None:
            return self.override(
                db,
                subject=subject,
                domain=domain,
                dt_from=dt_from,
                dt_to=dt_to,
                platform=platform,
                topic_id=topic_id,
            )
        return self._load_sql(
            db,
            subject=subject,
            domain=domain,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
        )

    @staticmethod
    def _load_sql(
        db: Session,
        *,
        subject: Subject,
        domain: str,
        dt_from: datetime,
        dt_to: datetime,
        platform: list[str] | None = None,
        topic_id: list[UUID] | None = None,
    ) -> _BacklinkDomainContext | None:
        if not domain:
            return None
        own_root = citation_root_for_subject(subject)
        if own_root and domain == registrable_from(own_root):
            return None

        eligible = _backlink_window_subquery(
            subject_id=subject.id,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
        )
        domain_filter = _backlink_domain_filter(domain, eligible)
        citation_count, chat_count, prompt_count = db.execute(
            select(
                func.coalesce(func.sum(CitationDomain.cite_count), 0),
                func.count(func.distinct(CitationDomain.response_id)),
                func.count(func.distinct(CitationDomain.prompt_id)),
            ).where(domain_filter)
        ).one()
        chat = int(chat_count or 0)
        if chat == 0:
            return None

        platform_rows = db.execute(
            select(LLMResponse.platform)
            .join(CitationDomain, CitationDomain.response_id == LLMResponse.id)
            .where(domain_filter)
            .distinct()
        ).all()
        platforms = sorted({str(row[0]) for row in platform_rows if row[0]})

        return _BacklinkDomainContext(
            domain=domain,
            citation_count=int(citation_count or 0),
            chat_count=chat,
            prompt_count=int(prompt_count or 0),
            platforms=platforms,
        )


_query_backlink_domain_context = _BacklinkDomainContextQuery()


def build_backlink_opportunities(
    db: Session,
    *,
    subject: Subject,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    order: str = "asc",
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """Aggregate external citation domains where own brand is not cited on source."""
    safe_page = max(1, page)
    safe_page_size = max(1, page_size)
    page_items, total = _query_backlink_domain_page(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        search=search,
        sort_by=sort_by,
        order=order,
        page=safe_page,
        page_size=safe_page_size,
    )
    if page_items and _query_backlink_domain_page.override is None:
        _attach_backlink_platforms(
            db,
            items=page_items,
            subject_id=subject.id,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
        )
    return {
        "items": page_items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
    }


def _backlink_mentioned_competitors(
    db: Session,
    *,
    subject: Subject,
    domain: str,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
) -> list[dict[str, str | None]]:
    from aperix_geo.services.sampling.citation.aggregate import (
        _competitor_domain_map,
        _url_matches_registrable,
    )
    from aperix_geo.services.sampling.citation.labels import page_mentioned_brand_names

    response_ids_stmt = _backlink_domain_response_ids_stmt(
        subject_id=subject_id,
        domain=domain,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )

    own = own_entity(subject)
    own_keys = {own.label.lower()}
    if subject.brand:
        own_keys.add(subject.brand.strip().lower())

    records = db.execute(
        select(CitationUrl).where(
            CitationUrl.response_id.in_(response_ids_stmt),
            _url_matches_registrable(CitationUrl.url, domain),
        )
    ).scalars().all()
    competitor_domains = _competitor_domain_map(subject)
    seen: set[str] = set()
    items: list[dict[str, str | None]] = []
    for record in records:
        analysis = record.llm_analysis if isinstance(record.llm_analysis, dict) else {}
        for name in page_mentioned_brand_names(analysis):
            key = name.lower()
            if key in own_keys or key in seen:
                continue
            seen.add(key)
            items.append({"label": name, "domain": competitor_domains.get(name)})
    return items


def _empty_backlink_detail(domain: str) -> dict[str, Any]:
    return {
        "domain": domain,
        "priority": "low",
        "platforms": [],
        "citation_count": 0,
        "citation_rate": 0,
        "chat_count": 0,
        "prompt_count": 0,
        "mentioned_competitors": [],
    }


def build_backlink_opportunity_detail(
    db: Session,
    *,
    subject: Subject,
    domain: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
) -> dict[str, Any]:
    domain = citation_registrable_key(domain)
    ctx = _query_backlink_domain_context(
        db,
        subject=subject,
        domain=domain,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    if ctx is None:
        return _empty_backlink_detail(domain)

    prompt_count = ctx.prompt_count

    from aperix_geo.services.analysis._query import count_responses_in_window

    response_total = count_responses_in_window(
        db,
        subject_id=subject.id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=None,
    )

    return {
        "domain": domain,
        "priority": backlink_priority(prompt_count, ctx.chat_count),
        "platforms": ctx.platforms,
        "citation_count": ctx.citation_count,
        "citation_rate": round(ctx.chat_count / response_total, 4) if response_total else 0,
        "chat_count": ctx.chat_count,
        "prompt_count": prompt_count,
        "mentioned_competitors": _backlink_mentioned_competitors(
            db,
            subject=subject,
            domain=domain,
            subject_id=subject.id,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
        ),
    }


def build_backlink_opportunity_urls_page(
    db: Session,
    *,
    subject: Subject,
    domain: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "count",
    order: str = "desc",
) -> dict[str, Any]:
    from aperix_geo.services.sampling.citation.aggregate import (
        _aggregate_url_row,
        _competitor_domain_map,
        _load_prompt_topic_maps,
        _normalize_pagination,
        _url_matches_registrable,
    )

    domain = citation_registrable_key(domain)
    ctx = _query_backlink_domain_context(
        db,
        subject=subject,
        domain=domain,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    safe_page, safe_page_size = _normalize_pagination(page, page_size)
    if ctx is None:
        return {
            "items": [],
            "total": 0,
            "page": safe_page,
            "page_size": safe_page_size,
            "response_total": 0,
        }

    response_ids_stmt = _backlink_domain_response_ids_stmt(
        subject_id=subject.id,
        domain=domain,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    response_total = ctx.chat_count
    count_expr = func.count(CitationUrl.id)
    grouped = (
        select(
            CitationUrl.url.label("url"),
            count_expr.label("count"),
        )
        .where(
            CitationUrl.response_id.in_(response_ids_stmt),
            _url_matches_registrable(CitationUrl.url, domain),
        )
        .group_by(CitationUrl.url)
    ).subquery()

    total = int(db.scalar(select(func.count()).select_from(grouped)) or 0)
    order_clause = grouped.c.count.asc() if order == "asc" else grouped.c.count.desc()
    offset = (safe_page - 1) * safe_page_size
    page_rows = db.execute(
        select(grouped.c.url, grouped.c.count)
        .order_by(order_clause, grouped.c.url.asc())
        .offset(offset)
        .limit(safe_page_size)
    ).all()
    _ = sort_by

    page_urls = [str(url) for url, _count in page_rows if url]
    if not page_urls:
        return {
            "items": [],
            "total": total,
            "page": safe_page,
            "page_size": safe_page_size,
            "response_total": response_total,
        }

    joined = db.execute(
        select(CitationUrl, LLMResponse.platform)
        .join(LLMResponse, CitationUrl.response_id == LLMResponse.id)
        .where(
            CitationUrl.url.in_(page_urls),
            CitationUrl.response_id.in_(response_ids_stmt),
        )
    ).all()

    grouped_records: dict[str, list[CitationUrl]] = defaultdict(list)
    platforms_by_url: dict[str, set[str]] = defaultdict(set)
    for record, platform_value in joined:
        grouped_records[record.url].append(record)
        if platform_value:
            platforms_by_url[record.url].add(str(platform_value))

    prompt_ids = {record.prompt_id for record, _platform in joined}
    prompt_map, topic_names = _load_prompt_topic_maps(db, prompt_ids)
    competitor_domains = _competitor_domain_map(subject)

    items = []
    for url in page_urls:
        row = _aggregate_url_row(
            url,
            grouped_records.get(url, []),
            total=response_total,
            competitor_domains=competitor_domains,
            prompt_map=prompt_map,
            topic_names=topic_names,
        )
        row["platforms"] = sorted(platforms_by_url.get(url, set()))
        items.append(row)

    return {
        "items": items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
        "response_total": response_total,
    }


def build_backlink_opportunity_prompts_page(
    db: Session,
    *,
    subject: Subject,
    domain: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "count",
    order: str = "desc",
) -> dict[str, Any]:
    from aperix_geo.services.sampling.citation.aggregate import _normalize_pagination, _url_matches_registrable

    domain = citation_registrable_key(domain)
    ctx = _query_backlink_domain_context(
        db,
        subject=subject,
        domain=domain,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    safe_page, safe_page_size = _normalize_pagination(page, page_size)
    if ctx is None:
        return {
            "items": [],
            "total": 0,
            "page": safe_page,
            "page_size": safe_page_size,
            "response_total": 0,
        }

    response_ids_stmt = _backlink_domain_response_ids_stmt(
        subject_id=subject.id,
        domain=domain,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    response_total = ctx.chat_count
    count_expr = func.count(CitationUrl.id)
    grouped = (
        select(
            CitationUrl.prompt_id.label("prompt_id"),
            count_expr.label("count"),
        )
        .where(
            CitationUrl.response_id.in_(response_ids_stmt),
            _url_matches_registrable(CitationUrl.url, domain),
        )
        .group_by(CitationUrl.prompt_id)
    ).subquery()

    total = int(db.scalar(select(func.count()).select_from(grouped)) or 0)
    order_clause = grouped.c.count.asc() if order == "asc" else grouped.c.count.desc()
    offset = (safe_page - 1) * safe_page_size
    page_rows = db.execute(
        select(grouped.c.prompt_id, grouped.c.count)
        .order_by(order_clause, grouped.c.prompt_id.asc())
        .offset(offset)
        .limit(safe_page_size)
    ).all()
    _ = sort_by

    page_prompt_ids = [prompt_id for prompt_id, _count in page_rows if prompt_id is not None]
    if not page_prompt_ids:
        return {
            "items": [],
            "total": total,
            "page": safe_page,
            "page_size": safe_page_size,
            "response_total": response_total,
        }

    prompts = db.execute(select(Prompt).where(Prompt.id.in_(page_prompt_ids))).scalars().all()
    prompt_map = {prompt.id: prompt for prompt in prompts}
    topic_ids = {prompt.topic_id for prompt in prompts}
    from aperix_geo.db.models import Topic

    topics = (
        db.execute(select(Topic).where(Topic.id.in_(topic_ids))).scalars().all()
        if topic_ids
        else []
    )
    topic_names = {str(topic.id): topic.name for topic in topics}
    count_by_prompt = {prompt_id: int(count) for prompt_id, count in page_rows}

    platform_rows = db.execute(
        select(CitationUrl.prompt_id, LLMResponse.platform)
        .join(LLMResponse, CitationUrl.response_id == LLMResponse.id)
        .where(
            CitationUrl.response_id.in_(response_ids_stmt),
            CitationUrl.prompt_id.in_(page_prompt_ids),
            _url_matches_registrable(CitationUrl.url, domain),
        )
        .distinct()
    ).all()
    platforms_by_prompt: dict[UUID, set[str]] = defaultdict(set)
    for prompt_id, platform_value in platform_rows:
        if prompt_id is not None and platform_value:
            platforms_by_prompt[prompt_id].add(str(platform_value))

    items = [
        {
            "id": str(prompt_id),
            "name": (prompt_map.get(prompt_id) and prompt_map[prompt_id].text) or "未知提示词",
            "topic_name": topic_names.get(
                str(prompt_map[prompt_id].topic_id) if prompt_id in prompt_map else "",
                "未知主题",
            ),
            "platforms": sorted(platforms_by_prompt.get(prompt_id, set())),
            "count": count_by_prompt.get(prompt_id, 0),
            "citation_rate": round(count_by_prompt.get(prompt_id, 0) / response_total, 4)
            if response_total
            else 0,
        }
        for prompt_id in page_prompt_ids
    ]
    return {
        "items": items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
        "response_total": response_total,
    }
