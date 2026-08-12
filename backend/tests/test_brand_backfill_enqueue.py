"""Tests for brand domain backfill enqueue dedupe."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.services.brand.backfill import maybe_enqueue_brand_domain_backfill


@patch("aperix_geo.utils.cache.redis_kv.redis_set_nx", return_value=False)
def test_backfill_skips_when_debounce_active(mock_set_nx: MagicMock) -> None:
    response_id = uuid4()

    with patch("aperix_geo.tasks.brand.backfill_brand_domain") as mock_task:
        maybe_enqueue_brand_domain_backfill(response_id)

    mock_set_nx.assert_called_once()
    mock_task.delay.assert_not_called()


@patch("aperix_geo.utils.cache.redis_kv.redis_set_nx", return_value=True)
def test_backfill_enqueues_when_debounce_acquired(mock_set_nx: MagicMock) -> None:
    response_id = uuid4()

    with patch("aperix_geo.tasks.brand.backfill_brand_domain") as mock_task:
        maybe_enqueue_brand_domain_backfill(response_id)

    mock_task.delay.assert_called_once_with(str(response_id))
