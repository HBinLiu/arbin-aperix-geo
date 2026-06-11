"""Tests for async brand domain backfill."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from aperix_geo.db.models import Brand, LLMResponse, LLMResponseSignal, Subject, SubjectType
from aperix_geo.services.brand.backfill import (
    backfill_brand_domains_for_response,
    maybe_enqueue_brand_domain_backfill,
)


def _subject() -> Subject:
    return Subject(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        type=SubjectType.brand,
        brand="Aperix",
        domain="aperix.com",
    )


def _response(*, subject: Subject) -> LLMResponse:
    return LLMResponse(
        id=uuid.uuid4(),
        sampling_job_id=uuid.uuid4(),
        prompt_id=uuid.uuid4(),
        platform="doubao",
        raw_text="推荐 Stripe 支付。",
        parsed={"urls": []},
        created_at=datetime.now(UTC),
    )


def _other_signal(*, response: LLMResponse, subject: Subject) -> LLMResponseSignal:
    return LLMResponseSignal(
        id=uuid.uuid4(),
        response_id=response.id,
        subject_id=subject.id,
        prompt_id=response.prompt_id,
        platform=response.platform,
        entity_id="other:stripe",
        entity_kind="other",
        brand_id=uuid.uuid4(),
        entity_label="Stripe",
        primary_domain="",
        created_at=datetime.now(UTC),
    )


@patch("aperix_geo.services.brand.backfill.resolve_brand_domain", return_value="stripe.com")
def test_backfill_updates_signal_and_brand(mock_resolve: MagicMock) -> None:
    subject = _subject()
    response = _response(subject=subject)
    signal = _other_signal(response=response, subject=subject)

    db = MagicMock()
    db.get.side_effect = lambda model, pk: {
        (LLMResponse, response.id): response,
        (Subject, subject.id): subject,
    }.get((model, pk))

    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [signal]
    db.execute.return_value = execute_result

    brand_row = Brand(id=signal.brand_id, tenant_id=subject.tenant_id, brand="Stripe", domain="stripe.com")
    with patch(
        "aperix_geo.services.brand.backfill.BrandSyncContext.load",
        return_value=MagicMock(catalog=MagicMock()),
    ), patch(
        "aperix_geo.services.brand.backfill.resolve_or_create_brand",
        return_value=brand_row,
    ) as mock_upsert:
        updated = backfill_brand_domains_for_response(db, response.id)

    assert updated == 1
    assert signal.primary_domain == "stripe.com"
    mock_resolve.assert_called_once()
    assert mock_resolve.call_args.kwargs["allow_search"] is True
    mock_upsert.assert_called_once()


@patch("aperix_geo.services.brand.backfill.resolve_brand_domain", return_value="")
def test_backfill_skips_when_search_unresolved(mock_resolve: MagicMock) -> None:
    subject = _subject()
    response = _response(subject=subject)
    signal = _other_signal(response=response, subject=subject)

    db = MagicMock()
    db.get.side_effect = lambda model, pk: {
        (LLMResponse, response.id): response,
        (Subject, subject.id): subject,
    }.get((model, pk))
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [signal]
    db.execute.return_value = execute_result

    with patch(
        "aperix_geo.services.brand.backfill.BrandSyncContext.load",
        return_value=MagicMock(catalog=MagicMock()),
    ):
        updated = backfill_brand_domains_for_response(db, response.id)

    assert updated == 0
    assert signal.primary_domain == ""


@patch("aperix_geo.tasks.brand.backfill_response_brand_domains.delay")
def test_maybe_enqueue_when_searxng_configured(mock_delay: MagicMock) -> None:
    response_id = uuid.uuid4()
    settings = MagicMock(searxng_base_url="http://127.0.0.1:8080")
    with patch("aperix_geo.services.brand.backfill.get_settings", return_value=settings):
        maybe_enqueue_brand_domain_backfill(response_id)
    mock_delay.assert_called_once_with(str(response_id))


@patch("aperix_geo.tasks.brand.backfill_response_brand_domains.delay")
def test_maybe_enqueue_skips_without_searxng(mock_delay: MagicMock) -> None:
    settings = MagicMock(searxng_base_url="")
    with patch("aperix_geo.services.brand.backfill.get_settings", return_value=settings):
        maybe_enqueue_brand_domain_backfill(uuid.uuid4())
    mock_delay.assert_not_called()
