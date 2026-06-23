"""Subject and competitor rank label helpers (shared by sampling and analysis)."""

from __future__ import annotations

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.utils.net import host_from, registrable_from


def _subject_rank_domain(subject: Subject) -> str:
    if subject.domain and subject.domain.strip():
        return registrable_from(subject.domain)
    if subject.website_url:
        return registrable_from(subject.website_url)
    return ""


def competitor_rank_label(*, brand: str = "", domain: str = "") -> str:
    d = registrable_from(domain.strip()) if domain.strip() else ""
    if d:
        return d
    return brand.strip()


def competitor_rank_domain(*, domain: str = "") -> str:
    if not domain.strip():
        return ""
    return registrable_from(domain) or host_from(domain)


def subject_rank_domain(subject: Subject) -> str:
    return _subject_rank_domain(subject)


def own_label(subject: Subject) -> str:
    domain = _subject_rank_domain(subject)
    if domain:
        return domain
    if subject.type == SubjectType.brand:
        return subject.brand or "own"
    return subject.domain or "own"


def rank_labels(subject: Subject) -> list[str]:
    own = own_label(subject)
    labels: list[str] = [own]
    for c in subject.competitors:
        lab = competitor_rank_label(brand=c.brand or "", domain=c.domain or "")
        if lab and lab not in labels:
            labels.append(lab)
    return labels
