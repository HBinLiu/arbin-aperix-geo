"""Tests for citation domain drill-down builders."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from aperix_geo.services.sampling.citation.aggregate import (
    domain_cite_stats,
    paginate_citation_domain_prompts,
    paginate_citation_urls,
)


def test_domain_cite_stats_empty_window() -> None:
    db = MagicMock()
    with patch(
        "aperix_geo.services.analysis._query.count_responses_in_window",
        return_value=0,
    ):
        count, response_total = domain_cite_stats(
            db,
            subject_id=uuid.uuid4(),
            dt_from=datetime(2026, 1, 1, tzinfo=UTC),
            dt_to=datetime(2026, 1, 31, tzinfo=UTC),
            domain="example.com",
        )
    assert count == 0
    assert response_total == 0
    db.execute.assert_not_called()


def test_paginate_citation_domain_prompts_empty_window() -> None:
    db = MagicMock()
    with patch(
        "aperix_geo.services.analysis._query.count_responses_in_window",
        return_value=0,
    ):
        result = paginate_citation_domain_prompts(
            db,
            subject_id=uuid.uuid4(),
            dt_from=datetime(2026, 1, 1, tzinfo=UTC),
            dt_to=datetime(2026, 1, 31, tzinfo=UTC),
            domain="example.com",
        )
    assert result["items"] == []
    assert result["response_total"] == 0


def test_paginate_citation_urls_with_domain_filter_empty_window() -> None:
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
            domain="example.com",
        )
    assert result["items"] == []
    assert result["response_total"] == 0
