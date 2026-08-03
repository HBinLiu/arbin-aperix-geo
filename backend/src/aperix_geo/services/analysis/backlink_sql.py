"""SQL aggregation for backlink opportunity windows."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.orm import Session

from aperix_geo.db.models import CitationDomain, DomainProfile, EntityKind, LLMResponse, LLMResponseSignal, Subject
from aperix_geo.services.analysis._query import response_ids_in_window_stmt
from aperix_geo.services.domain.taxonomy import normalize_domain_type
from aperix_geo.utils.net import registrable_from


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


def _backlink_row_from_sql(
    domain,
    citation_count,
    chat_count,
    prompt_count,
    domain_type: str = "",
    site_name: str = "",
) -> dict[str, Any] | None:
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
        "domain_type": normalize_domain_type(str(domain_type or "")),
        "site_name": str(site_name or "").strip(),
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
    own_kind = EntityKind.own.value
    window = response_ids_in_window_stmt(
        subject_id=subject_id,
        dt_from=dt_from,
        dt_to=dt_to,
        platform=platform,
        topic_id=topic_id,
        prompt_id=None,
    )
    cited_on_source = exists(
        select(1).where(
            LLMResponseSignal.response_id == LLMResponse.id,
            LLMResponseSignal.subject_id == subject_id,
            LLMResponseSignal.entity_kind == own_kind,
            LLMResponseSignal.cited_on_source.is_(True),
        )
    )
    return window.where(~cited_on_source)


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
                func.coalesce(DomainProfile.domain_type, "").label("domain_type"),
                func.coalesce(DomainProfile.site_name, "").label("site_name"),
                func.count().over().label("_total"),
            )
            .select_from(filtered)
            .outerjoin(
                DomainProfile,
                (DomainProfile.domain == filtered.c.domain) & (DomainProfile.deleted.is_(False)),
            )
            .order_by(*order_clauses)
            .offset(offset)
            .limit(safe_page_size)
        ).all()
        if not rows:
            total = int(db.scalar(select(func.count()).select_from(filtered)) or 0)
            return [], total

        total = int(rows[0]._total)

        items: list[dict[str, Any]] = []
        for domain, citation_count, chat_count, prompt_count, domain_type, site_name, _row_total in rows:
            row = _backlink_row_from_sql(
                domain,
                citation_count,
                chat_count,
                prompt_count,
                domain_type=str(domain_type or ""),
                site_name=str(site_name or ""),
            )
            if row is not None:
                items.append(row)
        return items, total


_query_backlink_domain_page = _BacklinkDomainPageQuery()
_query_backlink_domain_stats = _query_backlink_domain_page


def _attach_backlink_domain_types(db: Session, *, items: list[dict[str, Any]]) -> None:
    if not items:
        return
    domains = sorted({str(item.get("domain") or "").strip().lower() for item in items if item.get("domain")})
    if not domains:
        return
    rows = db.execute(
        select(DomainProfile.domain, DomainProfile.domain_type, DomainProfile.site_name).where(
            DomainProfile.domain.in_(domains),
            DomainProfile.deleted.is_(False),
        )
    ).all()
    type_map = {str(domain): normalize_domain_type(str(domain_type or "")) for domain, domain_type, _ in rows}
    name_map = {str(domain): str(site_name or "").strip() for domain, _, site_name in rows}
    for item in items:
        domain = str(item.get("domain") or "").strip().lower()
        item["domain_type"] = type_map.get(domain, normalize_domain_type(""))
        if not item.get("site_name"):
            item["site_name"] = name_map.get(domain, "")


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
        citation_count, chat_count, prompt_count, platform_values = db.execute(
            select(
                func.coalesce(func.sum(CitationDomain.cite_count), 0),
                func.count(func.distinct(CitationDomain.response_id)),
                func.count(func.distinct(CitationDomain.prompt_id)),
                func.array_agg(func.distinct(LLMResponse.platform)),
            )
            .join(LLMResponse, CitationDomain.response_id == LLMResponse.id)
            .where(domain_filter)
        ).one()
        chat = int(chat_count or 0)
        if chat == 0:
            return None

        platforms = sorted(
            {
                str(value)
                for value in (platform_values or [])
                if value not in (None, "")
            }
        )

        return _BacklinkDomainContext(
            domain=domain,
            citation_count=int(citation_count or 0),
            chat_count=chat,
            prompt_count=int(prompt_count or 0),
            platforms=platforms,
        )


_query_backlink_domain_context = _BacklinkDomainContextQuery()
