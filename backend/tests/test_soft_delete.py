"""Tests for ORM soft delete."""

from __future__ import annotations

import uuid

from aperix_geo.db.models import Competitor, Subject, SubjectType, Topic
from aperix_geo.db.delete import SoftDeleteSession


def test_session_delete_sets_deleted_flag() -> None:
    subject = Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.domain,
        domain="example.com",
        brand="Example",
    )
    SoftDeleteSession().delete(subject)
    assert subject.deleted is True


def test_soft_delete_method() -> None:
    topic = Topic(id=uuid.uuid4(), subject_id=uuid.uuid4(), name="支付")
    topic.soft_delete()
    assert topic.deleted is True


def test_competitor_soft_delete() -> None:
    row = Competitor(
        id=uuid.uuid4(),
        subject_id=uuid.uuid4(),
        domain="rival.com",
        brand="Rival",
    )
    SoftDeleteSession().delete(row)
    assert row.deleted is True
