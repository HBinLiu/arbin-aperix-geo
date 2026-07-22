"""Knowledge revision scheduling (verify + reindex)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.base import utc_now
from aperix_geo.db.models import Subject, SubjectKnowledge, SubjectType
from aperix_geo.services.knowledge.graph.extract import mark_extract_pending
from aperix_geo.services.subject.domain_fields import apply_subject_domain_fields
from aperix_geo.utils.net import ensure_brand, registrable_from


class KnowledgeNotFoundError(LookupError):
    """Subject has no knowledge row."""


def get_knowledge_row(db: Session, subject_id: UUID) -> SubjectKnowledge:
    knowledge = db.scalar(
        select(SubjectKnowledge).where(
            SubjectKnowledge.subject_id == subject_id,
            SubjectKnowledge.deleted.is_(False),
        )
    )
    if knowledge is None:
        raise KnowledgeNotFoundError(f"knowledge not found for subject {subject_id}")
    return knowledge


def _get_knowledge_row(db: Session, subject_id: UUID) -> SubjectKnowledge:
    """Backward-compatible alias."""
    return get_knowledge_row(db, subject_id)


def _clean_str_list(values: list[str] | None) -> list[str]:
    return [str(v).strip() for v in (values or []) if str(v).strip()]


def _sync_subject_from_identity(subject: Subject, identity: dict) -> None:
    if subject.type != SubjectType.brand:
        return
    name = str(identity.get("primary_name") or "").strip()
    if name:
        subject.brand = ensure_brand(name, domain=subject.domain or None)
    aliases = identity.get("aliases")
    if isinstance(aliases, list):
        subject.aliases = _clean_str_list(aliases)
    official_url = str(identity.get("official_url") or "").strip()
    _, website_url = apply_subject_domain_fields(
        subject_type=SubjectType.brand,
        raw_domain="",
        raw_website_url=official_url,
        probe=False,
    )
    subject.website_url = website_url
    subject.domain = registrable_from(website_url) or ""


def schedule_knowledge_reindex(
    db: Session,
    *,
    subject: Subject,
    knowledge: SubjectKnowledge,
    user_id: UUID,
) -> None:
    """Bump knowledge version after source changes. Caller must enqueue after commit."""
    _sync_subject_from_identity(subject, dict(knowledge.identity_json or {}))

    knowledge.version += 1
    knowledge.status = "verified"
    knowledge.verified_at = utc_now()
    knowledge.verified_by_user_id = user_id
    knowledge.index_status = "pending"
    knowledge.index_error = ""
    mark_extract_pending(knowledge)

    db.flush()
