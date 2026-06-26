"""Tests for configured-competitor → brand force sync."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import Brand, Competitor, EntityKind, Subject, SubjectType
from aperix_geo.services.brand.sync import force_sync_brand_from_competitor, force_sync_own_brand_from_subject


def test_force_sync_brand_from_competitor_overwrites_fields() -> None:
    subject_id = uuid.uuid4()
    brand_id = uuid.uuid4()
    competitor_id = uuid.uuid4()
    existing = Brand(
        id=brand_id,
        subject_id=subject_id,
        entity_kind=EntityKind.competitor.value,
        entity_id=str(competitor_id),
        brand="Old Name",
        domain="beta.com",
        website_url="https://old.example/",
        aliases=["legacy"],
        summary="old summary",
        source="setup",
    )
    competitor = Competitor(
        id=competitor_id,
        subject_id=subject_id,
        domain="beta.com",
        website_url="https://beta.com/",
        brand="Beta Corp",
        aliases=["Beta", "B"],
        summary="new summary",
    )

    db = MagicMock()
    with patch(
        "aperix_geo.services.brand.sync.find_brand_by_entity_id",
        return_value=existing,
    ):
        row = force_sync_brand_from_competitor(db, subject_id=subject_id, competitor=competitor)

    assert row is existing
    assert row.brand == "Beta Corp"
    assert row.domain == "beta.com"
    assert row.website_url == "https://beta.com/"
    assert row.aliases == ["Beta", "B"]
    assert row.summary == "new summary"
    assert row.entity_kind == EntityKind.competitor.value
    assert row.entity_id == str(competitor_id)
    db.flush.assert_called()


def test_force_sync_brand_from_competitor_releases_domain_from_open_set_row() -> None:
    """Editing a competitor to a domain held by an open-set brand must not 500."""
    subject_id = uuid.uuid4()
    competitor_id = uuid.uuid4()
    competitor_brand = Brand(
        id=uuid.uuid4(),
        subject_id=subject_id,
        entity_kind=EntityKind.competitor.value,
        entity_id=str(competitor_id),
        brand="Openi",
        domain="openi.cn",
        website_url="https://openi.cn/",
        aliases=[],
        summary="",
        source="setup",
    )
    open_set_brand = Brand(
        id=uuid.uuid4(),
        subject_id=subject_id,
        entity_kind=EntityKind.other.value,
        entity_id="",
        brand="Semrush",
        domain="semrush.com",
        website_url="https://semrush.com",
        aliases=[],
        summary="",
        source="sampling_open_set",
    )
    competitor = Competitor(
        id=competitor_id,
        subject_id=subject_id,
        domain="semrush.com",
        website_url="https://semrush.com/",
        brand="Semrush",
        aliases=[],
        summary="configured",
    )

    db = MagicMock()

    def find_by_entity(_db, *, subject_id, entity_id):
        if entity_id == str(competitor_id):
            return competitor_brand
        return None

    def find_by_domain(_db, *, subject_id, domain):
        if domain == "semrush.com":
            return open_set_brand
        return None

    with (
        patch("aperix_geo.services.brand.sync.find_brand_by_entity_id", side_effect=find_by_entity),
        patch("aperix_geo.services.brand.sync.find_brand_by_domain", side_effect=find_by_domain),
    ):
        row = force_sync_brand_from_competitor(db, subject_id=subject_id, competitor=competitor)

    assert row is competitor_brand
    assert row.domain == "semrush.com"
    assert row.brand == "Semrush"
    assert row.summary == "configured"
    assert open_set_brand.domain == ""


def test_force_sync_brand_from_competitor_matches_by_entity_id_after_domain_rename() -> None:
    subject_id = uuid.uuid4()
    competitor_id = uuid.uuid4()
    existing = Brand(
        id=uuid.uuid4(),
        subject_id=subject_id,
        entity_kind=EntityKind.competitor.value,
        entity_id=str(competitor_id),
        brand="Beta",
        domain="beta.com",
        website_url="https://beta.com/",
        aliases=[],
        summary="",
        source="setup",
    )
    competitor = Competitor(
        id=competitor_id,
        subject_id=subject_id,
        domain="gamma.com",
        website_url="https://gamma.com/",
        brand="Gamma",
        aliases=[],
        summary="renamed",
    )

    db = MagicMock()
    find = MagicMock(return_value=existing)
    with patch("aperix_geo.services.brand.sync.find_brand_by_entity_id", find):
        row = force_sync_brand_from_competitor(db, subject_id=subject_id, competitor=competitor)

    find.assert_any_call(db, subject_id=subject_id, entity_id=str(competitor_id))
    assert row.domain == "gamma.com"
    assert row.brand == "Gamma"
    assert row.summary == "renamed"


def test_force_sync_brand_falls_back_to_domain_when_entity_id_not_persisted() -> None:
    subject_id = uuid.uuid4()
    competitor_id = uuid.uuid4()
    existing = Brand(
        id=uuid.uuid4(),
        subject_id=subject_id,
        entity_kind=EntityKind.other.value,
        entity_id="",
        brand="智推时代",
        domain="zhituishidai.com",
        website_url="https://www.zhituishidai.com",
        aliases=[],
        summary="summary",
        source="sampling_open_set",
    )
    competitor = Competitor(
        id=competitor_id,
        subject_id=subject_id,
        domain="zhituishidai.com",
        website_url="https://www.zhituishidai.com",
        brand="智推时代",
        aliases=["GenOptima"],
        summary="summary",
    )

    db = MagicMock()
    with (
        patch(
            "aperix_geo.services.brand.sync.find_brand_by_entity_id",
            return_value=None,
        ) as by_entity,
        patch(
            "aperix_geo.services.brand.sync.find_brand_by_domain",
            return_value=existing,
        ) as by_domain,
    ):
        row = force_sync_brand_from_competitor(db, subject_id=subject_id, competitor=competitor)

    assert by_entity.call_count >= 1
    by_domain.assert_any_call(db, subject_id=subject_id, domain="zhituishidai.com")
    assert row is existing
    assert row.entity_id == str(competitor_id)
    assert row.entity_kind == EntityKind.competitor.value
    assert row.aliases == ["GenOptima"]


def test_update_competitor_by_id_updates_fields_without_inline_brand_sync() -> None:
    from aperix_geo.schemas.catalog import CompetitorItem
    from aperix_geo.services.competitor.persist import update_competitor_by_id

    subject = Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.domain,
        domain="aperix.com",
        brand="Aperix",
        website_url="https://aperix.com",
    )
    target_id = uuid.uuid4()
    target = Competitor(
        id=target_id,
        subject_id=subject.id,
        domain="beta.com",
        website_url="https://beta.com",
        brand="Beta",
        aliases=[],
        summary="",
    )
    subject.competitors = [target]
    db = MagicMock()

    updated = update_competitor_by_id(
        db,
        subject,
        competitor_id=target_id,
        item=CompetitorItem(
            domain="beta.com",
            website_url="https://beta.com",
            brand="Beta Corp",
            aliases=["B"],
            summary="updated",
        ),
    )

    assert updated.id == target_id
    assert updated.brand == "Beta Corp"
    assert updated.summary == "updated"


def test_force_sync_own_brand_from_subject_overwrites_fields() -> None:
    subject_id = uuid.uuid4()
    existing = Brand(
        id=uuid.uuid4(),
        subject_id=subject_id,
        entity_kind=EntityKind.own.value,
        entity_id="own",
        brand="Old Brand",
        domain="aperix.com",
        website_url="https://old.example/",
        aliases=["legacy"],
        summary="old profile",
        source="setup",
    )
    subject = Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.domain,
        domain="aperix.com",
        brand="Aperix",
        website_url="https://aperix.com/",
        aliases=["APX", "Aperix"],
        profile_summary="new profile",
    )

    db = MagicMock()
    with patch("aperix_geo.services.brand.sync.find_brand_by_entity_id", return_value=existing):
        row = force_sync_own_brand_from_subject(db, subject=subject)

    assert row is existing
    assert row.brand == "Aperix"
    assert row.domain == "aperix.com"
    assert row.website_url == "https://aperix.com/"
    assert row.aliases == ["APX", "Aperix"]
    assert row.summary == "new profile"
    assert row.entity_kind == EntityKind.own.value
    assert row.entity_id == "own"
    db.flush.assert_called()


def test_sync_subject_brands_from_setup_uses_force_sync_for_own_and_competitors() -> None:
    subject_id = uuid.uuid4()
    subject = Subject(
        id=subject_id,
        tenant_id=uuid.uuid4(),
        type=SubjectType.domain,
        domain="aperix.com",
        brand="Aperix",
        website_url="https://aperix.com/",
        aliases=[],
        profile_summary="profile",
    )
    subject.competitors = [
        Competitor(
            id=uuid.uuid4(),
            subject_id=subject_id,
            domain="beta.com",
            website_url="https://beta.com/",
            brand="Beta",
            aliases=[],
            summary="",
        )
    ]
    db = MagicMock()
    own_brand = Brand(id=uuid.uuid4(), subject_id=subject_id, entity_kind=EntityKind.own.value, brand="Aperix")
    competitor_brand = Brand(
        id=uuid.uuid4(), subject_id=subject_id, entity_kind=EntityKind.competitor.value, brand="Beta"
    )

    with (
        patch(
            "aperix_geo.services.brand.sync.force_sync_own_brand_from_subject",
            return_value=own_brand,
        ) as sync_own,
        patch(
            "aperix_geo.services.brand.sync.force_sync_brand_from_competitor",
            return_value=competitor_brand,
        ) as sync_competitor,
    ):
        from aperix_geo.services.brand.sync import sync_subject_brands_from_setup

        brands = sync_subject_brands_from_setup(db, subject=subject)

    sync_own.assert_called_once_with(db, subject=subject)
    sync_competitor.assert_called_once()
    assert brands["own"] is own_brand
    assert brands[str(subject.competitors[0].id)] is competitor_brand
