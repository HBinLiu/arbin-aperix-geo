"""Subject and competitor rank label helpers (shared by sampling and analysis)."""

from __future__ import annotations

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.utils.domains import registrable_domain
from aperix_geo.utils.url import hostname_from_url


def _subject_rank_domain(subject: Subject) -> str:
    if subject.domain and subject.domain.strip():
        return registrable_domain(subject.domain.strip()) or subject.domain.strip()
    if subject.website_url:
        host = hostname_from_url(subject.website_url)
        if host:
            return registrable_domain(host) or host
    return ""


def competitor_rank_label(*, brand: str = "", domain: str = "") -> str:
    d = registrable_domain(domain.strip()) if domain.strip() else ""
    if d:
        return d
    return brand.strip()


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
