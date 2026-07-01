"""Tests for tenant-scoped subject duplicate checks."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.services.setup.exceptions import SubjectDuplicateError
from aperix_geo.services.subject.duplicate import (
    assert_tenant_subject_unique,
    find_tenant_subject_duplicate,
)


def _mock_db_returning(subject: Subject | None) -> MagicMock:
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = subject
    return db


def test_assert_raises_for_existing_domain_subject() -> None:
    tenant_id = uuid4()
    existing = Subject(
        id=uuid4(),
        tenant_id=tenant_id,
        type=SubjectType.domain,
        domain="example.com",
        brand="Example",
        website_url="https://example.com",
    )
    db = _mock_db_returning(existing)

    with pytest.raises(SubjectDuplicateError, match="example.com"):
        assert_tenant_subject_unique(
            db,
            tenant_id=tenant_id,
            subject_type="domain",
            domain="https://www.example.com",
        )


def test_assert_raises_for_existing_brand_subject() -> None:
    tenant_id = uuid4()
    existing = Subject(
        id=uuid4(),
        tenant_id=tenant_id,
        type=SubjectType.brand,
        domain="",
        brand="八马茶业",
        website_url="",
    )
    db = _mock_db_returning(existing)

    with pytest.raises(SubjectDuplicateError, match="八马茶业"):
        assert_tenant_subject_unique(
            db,
            tenant_id=tenant_id,
            subject_type="brand",
            brand="八马茶业",
        )


def test_find_returns_none_when_unique() -> None:
    db = _mock_db_returning(None)
    assert (
        find_tenant_subject_duplicate(
            db,
            tenant_id=uuid4(),
            subject_type="domain",
            domain="new.com",
        )
        is None
    )
