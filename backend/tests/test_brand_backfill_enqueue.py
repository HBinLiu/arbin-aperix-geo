"""Tests for brand domain backfill enqueue dedupe."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.services.brand.backfill import maybe_enqueue_brand_domain_backfill


@patch("aperix_geo.utils.cache.redis_kv.redis_set_nx", return_value=False)
@patch("aperix_geo.services.brand.backfill.get_settings")
def test_backfill_skips_when_debounce_active(mock_settings: MagicMock, mock_set_nx: MagicMock) -> None:
    mock_settings.return_value.searxng_base_url = "http://searxng"
    response_id = uuid4()

    with patch("aperix_geo.tasks.brand.backfill_response_brand_domains") as mock_task:
        maybe_enqueue_brand_domain_backfill(response_id)

    mock_set_nx.assert_called_once()
    mock_task.delay.assert_not_called()


@patch("aperix_geo.utils.cache.redis_kv.redis_set_nx", return_value=True)
@patch("aperix_geo.services.brand.backfill.get_settings")
def test_backfill_enqueues_when_debounce_acquired(mock_settings: MagicMock, mock_set_nx: MagicMock) -> None:
    mock_settings.return_value.searxng_base_url = "http://searxng"
    response_id = uuid4()

    with patch("aperix_geo.tasks.brand.backfill_response_brand_domains") as mock_task:
        maybe_enqueue_brand_domain_backfill(response_id)

    mock_task.delay.assert_called_once_with(str(response_id))
