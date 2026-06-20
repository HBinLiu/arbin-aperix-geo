"""Platform analysis API payload tests."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from aperix_geo.services.analysis.platform import (
    _build_matrix_cells,
    _build_platform_charts,
    build_platform_analysis,
)
from aperix_geo.services.analysis.performance import platform_performance_rows
from aperix_geo.services.analysis.signal_load import LLMResponseSignalRow


def _signal(
    *,
    platform: str,
    day: int = 1,
    entity_id: str = "own",
    mention_count: int = 1,
    mentioned: bool = True,
) -> LLMResponseSignalRow:
    subject_id = uuid4()
    return LLMResponseSignalRow(
        response_id=uuid4(),
        subject_id=subject_id,
        prompt_id=uuid4(),
        platform=platform,
        entity_id=entity_id,
        entity_kind="own" if entity_id == "own" else "competitor",
        brand_id=uuid4(),
        mentioned=mentioned,
        mention_count=mention_count,
        mention_rank=1,
        sentiment_score=50.0,
        sentiment_reason="",
        has_domain_link=False,
        cited_on_source=False,
        created_at=datetime(2026, 5, day, tzinfo=timezone.utc),
    )


def test_build_platform_charts_merges_platforms_by_date():
    subject = MagicMock()
    signals = [_signal(platform="deepseek", day=1), _signal(platform="doubao", day=1)]

    charts = _build_platform_charts(
        ["deepseek", "doubao"],
        signals,
        subject=subject,
        entity_id="own",
    )

    visibility = charts["visibility"]["current"]
    assert len(visibility) == 1
    assert set(visibility[0]["values"].keys()) == {"deepseek", "doubao"}


@patch("aperix_geo.services.analysis.platform.load_topic_prompt_catalog")
@patch("aperix_geo.services.analysis.platform.load_llm_response_signals")
@patch("aperix_geo.services.analysis.platform.list_analysis_entities")
@patch("aperix_geo.services.analysis.platform.resolve_analysis_entity")
@patch("aperix_geo.services.analysis.platform.resolve_platforms_for_sampling")
def test_build_platform_analysis_payload_shape(
    mock_resolve_platforms,
    mock_resolve_entity,
    mock_list_entities,
    mock_load_signals,
    mock_load_catalog,
):
    mock_resolve_platforms.return_value = ["deepseek", "doubao"]
    mock_resolve_entity.return_value = SimpleNamespace(id="own", label="own.com")
    mock_list_entities.return_value = [SimpleNamespace(id="own", label="own.com", kind="own")]
    mock_load_catalog.return_value = ({}, {}, {})
    mock_load_signals.return_value = [_signal(platform="doubao", day=2)]

    db = MagicMock()
    subject = MagicMock()
    subject.id = uuid4()
    subject.domain = "example.com"
    subject.website_url = None
    subject.type = "domain"
    subject.competitors = []

    dt_from = datetime(2026, 5, 1, tzinfo=timezone.utc)
    dt_to = datetime(2026, 5, 7, tzinfo=timezone.utc)
    result = build_platform_analysis(
        db,
        subject=subject,
        dt_from=dt_from,
        dt_to=dt_to,
        matrix_row="competitor",
    )

    assert result["entity_id"] == "own"
    assert result["matrix_row"] == "competitor"
    assert "charts" in result
    assert "own_label" not in result
    assert "platform_catalog" not in result
    assert "platforms" not in result
    assert "series" not in result
    assert set(result["charts"].keys()) == {
        "visibility",
        "share_voice",
        "citation",
        "average_rank",
        "sentiment",
    }

    matrix_platforms = {cell["platform_id"] for cell in result["matrix_cells"]["current"]}
    assert matrix_platforms == {"deepseek", "doubao"}

    mock_resolve_platforms.assert_called_once_with(subject, None)


def test_platform_performance_share_voice_uses_platform_voice_pool():
    subject = MagicMock()
    subject.type = "domain"
    subject.website_url = None
    signals = [
        _signal(platform="doubao", entity_id="own", mention_count=2),
        _signal(platform="doubao", entity_id="comp-a", mention_count=18),
        _signal(platform="deepseek", entity_id="own", mention_count=8),
    ]

    rows = platform_performance_rows(signals, subject=subject, entity_id="own")
    by_platform = {row["platform"]: row for row in rows}

    assert by_platform["doubao"]["share_voice"] == 0.1
    assert by_platform["deepseek"]["share_voice"] == 1.0


def test_matrix_and_performance_metrics_align_for_focus_entity():
    subject = MagicMock()
    subject.type = "domain"
    subject.domain = "example.com"
    subject.website_url = None
    subject.competitors = []
    focus_entity = SimpleNamespace(id="own", label="example.com")
    entities = [SimpleNamespace(id="own", label="example.com", kind="own")]
    signals = [
        _signal(platform="doubao", entity_id="own", mention_count=2),
        _signal(platform="doubao", entity_id="comp-a", mention_count=18),
    ]

    matrix_cells = _build_matrix_cells(
        signals,
        row_dimension="competitor",
        platform_ids=["doubao"],
        subject=subject,
        entities=entities,
        focus_entity=focus_entity,
        prompt_to_topic={},
    )
    performance = platform_performance_rows(signals, subject=subject, entity_id="own")

    own_cell = next(cell for cell in matrix_cells if cell["row_id"] == "own")
    assert own_cell["share_voice"] == performance[0]["share_voice"]
    assert own_cell["visibility_rate"] == performance[0]["visibility_rate"]
    assert own_cell["citation_rate"] == performance[0]["citation_rate"]


def test_platform_chart_single_day_matches_performance_for_rate_metrics():
    subject = MagicMock()
    subject.type = "domain"
    subject.website_url = None
    signals = [
        _signal(platform="doubao", day=1, entity_id="own", mention_count=2, mentioned=True),
        _signal(platform="doubao", day=1, entity_id="comp-a", mention_count=8, mentioned=True),
    ]

    charts = _build_platform_charts(["doubao"], signals, subject=subject, entity_id="own")
    performance = platform_performance_rows(signals, subject=subject, entity_id="own")[0]
    last_point = charts["visibility"]["current"][-1]["values"]["doubao"]

    assert last_point == performance["visibility_rate"]
    assert charts["share_voice"]["current"][-1]["values"]["doubao"] == performance["share_voice"]
