"""Backlink opportunity analysis."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, not_, or_, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import CitationDomain, CitationUrl, EntityKind, LLMResponse, LLMResponseSignal, Prompt, Subject
from aperix_geo.services.analysis.entity import own_entity
from aperix_geo.utils.url import host_matches_root


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
        row["host"],
    )


def _filter_backlink_by_search(items: list[dict[str, Any]], search: str | None) -> list[dict[str, Any]]:
    query = (search or "").strip().lower()
    if not query:
        return items
    return [item for item in items if query in item["host"].lower()]


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
            key=lambda row: (_BACKLINK_PRIORITY_ORDER.get(row["priority"], 9), row["host"]),
            reverse=reverse,
        )
    if sort_by == "prompt_count":
        return sorted(items, key=lambda row: row["prompt_count"], reverse=reverse)
    if sort_by == "chat_count":
        return sorted(items, key=lambda row: row["chat_count"], reverse=reverse)
    if sort_by == "citation_count":
        return sorted(items, key=lambda row: row["citation_count"], reverse=reverse)
    return sorted(items, key=_backlink_row_rank_key)


@dataclass(frozen=True)
class _BacklinkHostContext:
    host: str
    response_ids: frozenset[UUID]
    citation_count: int
    chat_count: int
    prompt_ids: frozenset[UUID]
    platforms: list[str]


def _normalize_backlink_host(host: str) -> str:
    return (host or "").strip().lower()


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


def _backlink_host_domain_filter(host: str, eligible_subq) -> Any:
    return and_(
        CitationDomain.response_id.in_(select(eligible_subq.c.id)),
        CitationDomain.domain == host,
    )


def _backlink_host_response_ids_stmt(
    *,
    subject_id: UUID,
    host: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
):
    host_key = _normalize_backlink_host(host)
    eligible = _backlink_window_subquery(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    return select(CitationDomain.response_id).where(_backlink_host_domain_filter(host_key, eligible)).distinct()


def _exclude_own_domain(domain_column, own_root: str | None):
    if not own_root:
        return True
    root = own_root.lower().replace("www.", "")
    return not_(
        or_(
            domain_column == root,
            domain_column == f"www.{root}",
            domain_column.like(f"%.{root}"),
        )
    )


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


class _BacklinkHostStatsQuery:
    """Patchable host stats query (tests assign to `.override`)."""

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
    ) -> list[dict[str, Any]]:
        if self.override is not None:
            return self.override(
                db,
                subject=subject,
                dt_from=dt_from,
                dt_to=dt_to,
                platform=platform,
                topic_id=topic_id,
            )
        return self._load_sql(
            db,
            subject=subject,
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
        dt_from: datetime,
        dt_to: datetime,
        platform: list[str] | None = None,
        topic_id: list[UUID] | None = None,
    ) -> list[dict[str, Any]]:
        eligible = _backlink_eligible_response_ids_stmt(
            subject_id=subject.id,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
        ).subquery()
        own_root = citation_root_for_subject(subject)
        grouped = (
            select(
                CitationDomain.domain.label("host"),
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

        rows = db.execute(
            select(
                grouped.c.host,
                grouped.c.citation_count,
                grouped.c.chat_count,
                grouped.c.prompt_count,
            ).where(grouped.c.chat_count > 0)
        ).all()

        items: list[dict[str, Any]] = []
        for host, citation_count, chat_count, prompt_count in rows:
            host_key = str(host or "").strip().lower()
            if not host_key:
                continue
            chat = int(chat_count or 0)
            prompts = int(prompt_count or 0)
            items.append(
                {
                    "id": host_key,
                    "host": host_key,
                    "platforms": [],
                    "priority": backlink_priority(prompts, chat),
                    "citation_count": int(citation_count or 0),
                    "prompt_count": prompts,
                    "chat_count": chat,
                }
            )
        return items


_query_backlink_host_stats = _BacklinkHostStatsQuery()


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
    page_hosts = [item["host"] for item in items]
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
            CitationDomain.domain.in_(page_hosts),
        )
    ).all()
    platforms_by_host: dict[str, set[str]] = defaultdict(set)
    for domain, platform_value in platform_rows:
        host_key = str(domain or "").strip().lower()
        if host_key and platform_value:
            platforms_by_host[host_key].add(str(platform_value))
    for item in items:
        item["platforms"] = sorted(platforms_by_host.get(item["host"], set()))


class _BacklinkHostContextQuery:
    """Patchable single-host context query (tests assign to `.override`)."""

    override: Callable[..., _BacklinkHostContext | None] | None = None

    def __call__(
        self,
        db: Session,
        *,
        subject: Subject,
        host: str,
        dt_from: datetime,
        dt_to: datetime,
        platform: list[str] | None = None,
        topic_id: list[UUID] | None = None,
    ) -> _BacklinkHostContext | None:
        if self.override is not None:
            return self.override(
                db,
                subject=subject,
                host=host,
                dt_from=dt_from,
                dt_to=dt_to,
                platform=platform,
                topic_id=topic_id,
            )
        return self._load_sql(
            db,
            subject=subject,
            host=host,
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
        host: str,
        dt_from: datetime,
        dt_to: datetime,
        platform: list[str] | None = None,
        topic_id: list[UUID] | None = None,
    ) -> _BacklinkHostContext | None:
        host_key = _normalize_backlink_host(host)
        if not host_key:
            return None
        own_root = citation_root_for_subject(subject)
        if own_root and host_matches_root(host_key, own_root):
            return None

        eligible = _backlink_window_subquery(
            subject_id=subject.id,
            dt_from=dt_from,
            dt_to=dt_to,
            platform=platform,
            topic_id=topic_id,
        )
        domain_filter = _backlink_host_domain_filter(host_key, eligible)
        citation_count, chat_count = db.execute(
            select(
                func.coalesce(func.sum(CitationDomain.cite_count), 0),
                func.count(func.distinct(CitationDomain.response_id)),
            ).where(domain_filter)
        ).one()
        chat = int(chat_count or 0)
        if chat == 0:
            return None

        response_ids = frozenset(db.scalars(select(CitationDomain.response_id).where(domain_filter)).all())
        prompt_ids = frozenset(db.scalars(select(CitationDomain.prompt_id).where(domain_filter)).all())
        platform_rows = db.execute(
            select(LLMResponse.platform)
            .join(CitationDomain, CitationDomain.response_id == LLMResponse.id)
            .where(domain_filter)
            .distinct()
        ).all()
        platforms = sorted({str(row[0]) for row in platform_rows if row[0]})

        return _BacklinkHostContext(
            host=host_key,
            response_ids=response_ids,
            citation_count=int(citation_count or 0),
            chat_count=chat,
            prompt_ids=prompt_ids,
            platforms=platforms,
        )


_query_backlink_host_context = _BacklinkHostContextQuery()


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
    """Aggregate external citation hosts where own brand is not cited on source."""
    items = _query_backlink_host_stats(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    filtered = _filter_backlink_by_search(items, search)
    sorted_items = _sort_backlink_items(filtered, sort_by=sort_by, order=order)
    safe_page = max(1, page)
    safe_page_size = max(1, page_size)
    total = len(sorted_items)
    start = (safe_page - 1) * safe_page_size
    page_items = sorted_items[start : start + safe_page_size]
    if page_items and _query_backlink_host_stats.override is None:
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
    host: str,
    subject_id: UUID,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None,
    topic_id: list[UUID] | None,
) -> list[dict[str, str | None]]:
    from aperix_geo.services.sampling.citation.aggregate import (
        _competitor_domain_map,
        _url_matches_host,
    )
    from aperix_geo.services.sampling.citation.labels import page_mentioned_brand_names

    host_key = _normalize_backlink_host(host)
    response_ids_stmt = _backlink_host_response_ids_stmt(
        subject_id=subject_id,
        host=host_key,
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
            _url_matches_host(CitationUrl.url, host_key),
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


def _empty_backlink_detail(host: str) -> dict[str, Any]:
    return {
        "host": host,
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
    host: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
) -> dict[str, Any]:
    host = _normalize_backlink_host(host)
    ctx = _query_backlink_host_context(
        db,
        subject=subject,
        host=host,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
    )
    if ctx is None:
        return _empty_backlink_detail(host)

    prompt_count = len(ctx.prompt_ids)

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
        "host": host,
        "priority": backlink_priority(prompt_count, ctx.chat_count),
        "platforms": ctx.platforms,
        "citation_count": ctx.citation_count,
        "citation_rate": round(ctx.chat_count / response_total, 4) if response_total else 0,
        "chat_count": ctx.chat_count,
        "prompt_count": prompt_count,
        "mentioned_competitors": _backlink_mentioned_competitors(
            db,
            subject=subject,
            host=host,
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
    host: str,
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
        _url_matches_host,
    )

    host = _normalize_backlink_host(host)
    ctx = _query_backlink_host_context(
        db,
        subject=subject,
        host=host,
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

    response_ids_stmt = _backlink_host_response_ids_stmt(
        subject_id=subject.id,
        host=host,
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
            _url_matches_host(CitationUrl.url, host),
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
    host: str,
    dt_from: datetime,
    dt_to: datetime,
    platform: list[str] | None = None,
    topic_id: list[UUID] | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "count",
    order: str = "desc",
) -> dict[str, Any]:
    from aperix_geo.services.sampling.citation.aggregate import _normalize_pagination, _url_matches_host

    host = _normalize_backlink_host(host)
    ctx = _query_backlink_host_context(
        db,
        subject=subject,
        host=host,
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

    response_ids_stmt = _backlink_host_response_ids_stmt(
        subject_id=subject.id,
        host=host,
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
            _url_matches_host(CitationUrl.url, host),
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
            _url_matches_host(CitationUrl.url, host),
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