"""Subject CRUD."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from aperix_geo.api.deps import CurrentUser, DbSession, get_subject_for_user
from aperix_geo.api.routes import subject_setup
from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.schemas.catalog import SubjectCreate, SubjectOut, SubjectUpdate
from aperix_geo.services.subject.domain_fields import apply_subject_domain_fields
from aperix_geo.services.sampling.workflow import validate_sampling_interval
from aperix_geo.services.sampling.subject import validate_sampling_platforms
from aperix_geo.services.subject.rules import validate_subject_fields
from aperix_geo.utils.coerce import normalize_monitoring_scope
from aperix_geo.utils.domains import ensure_brand

router = APIRouter(prefix="/subjects", tags=["subjects"])
router.include_router(subject_setup.router)


@router.get("", response_model=list[SubjectOut])
def list_subjects(
    db: DbSession,
    current: CurrentUser,
) -> list[Subject]:
    return list(
        db.execute(
            select(Subject)
            .where(Subject.tenant_id == current.tenant_id)
            .order_by(Subject.created_at.desc())
        )
        .scalars()
        .all()
    )


@router.post("", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
def create_subject(
    body: SubjectCreate,
    db: DbSession,
    current: CurrentUser,
) -> Subject:
    st = SubjectType(body.type.value)
    domain_val = body.domain.strip() if body.domain else ""
    website_val = (body.website_url or "").strip()
    domain, website_url = apply_subject_domain_fields(
        subject_type=st,
        raw_domain=domain_val,
        raw_website_url=website_val,
    )
    sub = Subject(
        tenant_id=current.tenant_id,
        type=st,
        domain=domain,
        brand=ensure_brand(body.brand, domain=domain if st == SubjectType.domain else None),
        website_url=website_url,
        aliases=list(body.aliases or []),
        monitoring_scope=normalize_monitoring_scope(
            body.monitoring_scope.model_dump(exclude_none=True) if body.monitoring_scope else None
        ),
    )
    validate_subject_fields(sub)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.get("/{subject_id}", response_model=SubjectOut)
def get_subject(
    subject_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> Subject:
    return get_subject_for_user(db, current, subject_id)


@router.patch("/{subject_id}", response_model=SubjectOut)
def update_subject(
    subject_id: UUID,
    body: SubjectUpdate,
    db: DbSession,
    current: CurrentUser,
) -> Subject:
    sub = get_subject_for_user(db, current, subject_id)
    if body.domain is not None or body.website_url is not None:
        raw_domain = body.domain.strip() if body.domain is not None else sub.domain
        if body.website_url is not None:
            raw_website = body.website_url.strip()
        elif body.domain is not None and body.domain.strip() != sub.domain:
            raw_website = ""
        else:
            raw_website = sub.website_url
        domain, website_url = apply_subject_domain_fields(
            subject_type=sub.type,
            raw_domain=raw_domain,
            raw_website_url=raw_website,
        )
        sub.domain = domain
        sub.website_url = website_url
    if body.brand is not None:
        sub.brand = ensure_brand(
            body.brand,
            domain=sub.domain if sub.type == SubjectType.domain else None,
        )
    if body.aliases is not None:
        sub.aliases = list(body.aliases)
    if body.monitoring_scope is not None:
        sub.monitoring_scope = normalize_monitoring_scope(
            body.monitoring_scope.model_dump(exclude_none=True)
        )
    if body.profile_summary is not None:
        sub.profile_summary = body.profile_summary
    if body.sampling_platforms is not None:
        sub.sampling_platforms = validate_sampling_platforms(body.sampling_platforms)
    if body.sampling_interval is not None:
        try:
            sub.sampling_interval = validate_sampling_interval(body.sampling_interval)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    validate_subject_fields(sub)
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    subject_id: UUID,
    db: DbSession,
    current: CurrentUser,
) -> None:
    sub = get_subject_for_user(db, current, subject_id)
    db.delete(sub)
    db.commit()
