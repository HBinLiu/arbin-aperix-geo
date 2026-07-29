"""Tests for tenant member invite and management."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from aperix_geo.db.models import User, UserRole
from aperix_geo.services.auth import tenant_members as member_svc


def _user(*, tenant_id: uuid.UUID | None = None, role: str = UserRole.admin.value) -> User:
    return User(
        id=uuid.uuid4(),
        tenant_id=tenant_id or uuid.uuid4(),
        phone="13800138000",
        email="",
        role=role,
    )


def test_require_tenant_admin_rejects_member() -> None:
    user = _user(role=UserRole.member.value)
    with pytest.raises(HTTPException) as exc:
        member_svc.require_tenant_admin(user)
    assert exc.value.status_code == 403


def test_validate_invite_phone_rejects_existing_member() -> None:
    tenant_id = uuid.uuid4()
    db = MagicMock()
    existing = _user(tenant_id=tenant_id)
    with patch.object(member_svc, "_tenant_member_by_phone", return_value=existing):
        with pytest.raises(HTTPException) as exc:
            member_svc.validate_invite_phone(db, tenant_id=tenant_id, phone_raw="13800138001")
    assert exc.value.status_code == 409


def test_validate_invite_phone_rejects_other_tenant() -> None:
    tenant_id = uuid.uuid4()
    db = MagicMock()
    other = _user(tenant_id=uuid.uuid4())
    with patch.object(member_svc, "_tenant_member_by_phone", return_value=None):
        with patch.object(member_svc, "_user_by_phone", return_value=other):
            with pytest.raises(HTTPException) as exc:
                member_svc.validate_invite_phone(db, tenant_id=tenant_id, phone_raw="13800138001")
    assert exc.value.status_code == 409


def test_remove_tenant_member_rejects_self() -> None:
    actor = _user()
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        member_svc.remove_tenant_member(
            db,
            tenant_id=actor.tenant_id,
            actor=actor,
            member_id=actor.id,
        )
    assert exc.value.status_code == 400


def test_remove_tenant_member_rejects_last_admin() -> None:
    tenant_id = uuid.uuid4()
    actor = _user(tenant_id=tenant_id)
    target = _user(tenant_id=tenant_id, role=UserRole.admin.value)
    db = MagicMock()
    db.get.return_value = target
    with patch.object(member_svc, "_count_tenant_admins", return_value=0):
        with pytest.raises(HTTPException) as exc:
            member_svc.remove_tenant_member(
                db,
                tenant_id=tenant_id,
                actor=actor,
                member_id=target.id,
            )
    assert exc.value.status_code == 400
