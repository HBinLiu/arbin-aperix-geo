"""Subject context helpers for mention discovery / ABSA."""

from __future__ import annotations

from aperix_geo.db.models import Subject


def subject_track_context(subject: Subject | None) -> str:
    """Short vertical context for same-track mention/sentiment prompts."""
    if subject is None:
        return ""
    niche = subject.niche_profile if isinstance(subject.niche_profile, dict) else {}
    industry = str(niche.get("industry") or "").strip()
    if industry:
        return industry
    for field in (subject.profile_summary, subject.summary):
        text = str(field or "").strip()
        if text:
            return text[:240]
    return ""
