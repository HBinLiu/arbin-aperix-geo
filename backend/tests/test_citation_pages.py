"""Tests for paginated citation domain/URL list builders."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from aperix_geo.services.sampling.citation.aggregate import (
    domain_search_needle,
    paginate_citation_domains,
    paginate_citation_urls,
    url_search_needle,
)


def test_domain_search_needle_from_url() -> None:
    assert domain_search_needle("https://docs.stripe.com/payments") == "stripe.com"
    assert domain_search_needle("stripe.com") == "stripe.com"


def test_url_search_needle_lowercases() -> None:
    assert url_search_needle("  HTTPS://Example.com/Path ") == "https://example.com/path"


def test_paginate_citation_domains_empty_window() -> None:
    db = MagicMock()
    with patch(
        "aperix_geo.services.analysis._query.count_responses_in_window",
        return_value=0,
    ):
        result = paginate_citation_domains(
            db,
            subject_id=uuid.uuid4(),
            dt_from=datetime(2026, 1, 1, tzinfo=UTC),
            dt_to=datetime(2026, 1, 31, tzinfo=UTC),
        )
    assert result == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 10,
        "response_total": 0,
    }
    db.execute.assert_not_called()


def test_paginate_citation_urls_empty_window() -> None:
    db = MagicMock()
    with patch(
        "aperix_geo.services.analysis._query.count_responses_in_window",
        return_value=0,
    ):
        result = paginate_citation_urls(
            db,
            subject_id=uuid.uuid4(),
            dt_from=datetime(2026, 1, 1, tzinfo=UTC),
            dt_to=datetime(2026, 1, 31, tzinfo=UTC),
        )
    assert result["items"] == []
    assert result["response_total"] == 0
