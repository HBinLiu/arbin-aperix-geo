"""Tenant member invite and listing (real-time phone OTP)."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import User, UserRole
from aperix_geo.services.auth import otp as otp_svc
from aperix_geo.services.billing.exceptions import QuotaExceededError, SubscriptionInactiveError
from aperix_geo.services.billing.http import billing_http_exception
from aperix_geo.services.billing.quota import assert_team_member_capacity
from aperix_geo.utils.contact import mask_phone_cn, normalize_phone_cn

_INVITE_ROLES = frozenset({UserRole.member.value, UserRole.readonly.value})


def require_tenant_admin(user: User) -> None:
    if user.role != UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")


def _user_by_phone(db: Session, phone_norm: str) -> User | None:
    return db.execute(
        select(User).where(User.phone == phone_norm, User.deleted.is_(False)),
    ).scalar_one_or_none()


def _tenant_member_by_phone(db: Session, *, tenant_id: uuid.UUID, phone_norm: str) -> User | None:
    return db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.phone == phone_norm,
            User.deleted.is_(False),
        ),
    ).scalar_one_or_none()


def _count_tenant_admins(db: Session, tenant_id: uuid.UUID, *, exclude_user_id: uuid.UUID | None = None) -> int:
    q = select(User.id).where(
        User.tenant_id == tenant_id,
        User.role == UserRole.admin.value,
        User.is_active.is_(True),
        User.deleted.is_(False),
    )
    if exclude_user_id is not None:
        q = q.where(User.id != exclude_user_id)
    return len(list(db.execute(q).scalars().all()))


def validate_invite_phone(db: Session, *, tenant_id: uuid.UUID, phone_raw: str) -> str:
    try:
        phone_norm = normalize_phone_cn(phone_raw)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if _tenant_member_by_phone(db, tenant_id=tenant_id, phone_norm=phone_norm):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该手机号已是团队成员")

    existing = _user_by_phone(db, phone_norm)
    if existing is not None and existing.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该手机号已注册其他团队",
        )
    try:
        assert_team_member_capacity(db, tenant_id, adding=1)
    except (SubscriptionInactiveError, QuotaExceededError) as exc:
        raise billing_http_exception(exc, inactive_detail="订阅已过期，无法邀请成员") from exc
    return phone_norm


def list_tenant_members(db: Session, tenant_id: uuid.UUID) -> list[dict[str, object]]:
    rows = list(
        db.execute(
            select(User)
            .where(User.tenant_id == tenant_id, User.deleted.is_(False))
            .order_by(User.created_at.desc()),
        ).scalars().all()
    )
    return [
        {
            "id": user.id,
            "phone": mask_phone_cn(user.phone) if user.phone else "",
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }
        for user in rows
    ]


def invite_tenant_member(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    inviter: User,
    phone_raw: str,
    code: str,
    role: str = UserRole.member.value,
    settings,
) -> User:
    require_tenant_admin(inviter)
    phone_norm = validate_invite_phone(db, tenant_id=tenant_id, phone_raw=phone_raw)

    invite_role = role.strip() or UserRole.member.value
    if invite_role not in _INVITE_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="无效的成员角色")

    if not otp_svc.verify_code(
        settings=settings,
        purpose="invite",
        channel="phone",
        target_raw=phone_norm,
        code=code,
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码无效或已过期")

    user = User(
        tenant_id=tenant_id,
        phone=phone_norm,
        email="",
        role=invite_role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def remove_tenant_member(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    actor: User,
    member_id: uuid.UUID,
) -> None:
    require_tenant_admin(actor)
    if actor.id == member_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能移除当前登录账号")

    member = db.get(User, member_id)
    if not member or member.tenant_id != tenant_id or member.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="成员不存在")

    if member.role == UserRole.admin.value and _count_tenant_admins(db, tenant_id, exclude_user_id=member.id) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能移除最后一个管理员")

    db.delete(member)
    db.commit()
