"""Subject business rules."""

from fastapi import HTTPException, status

from aperix_geo.db.models import Subject, SubjectType


def validate_subject_fields(subject: Subject) -> None:
    if subject.type == SubjectType.domain:
        if not subject.domain or not subject.domain.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="domain type requires non-empty domain",
            )
    elif subject.type == SubjectType.brand:
        if not subject.brand or not subject.brand.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="brand type requires brand",
            )


def validate_brand_competitors(subject: Subject) -> None:
    if subject.type != SubjectType.brand:
        return
    has_brand_only = any(
        (c.brand or "").strip() and not (c.domain or "").strip() for c in subject.competitors
    )
    if not has_brand_only:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="brand subject requires at least one competitor brand",
        )
