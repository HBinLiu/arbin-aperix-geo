"""Read-time aggregates for MVP dashboards."""

from __future__ import annotations

from aperix_geo.services.analysis._labels import own_label as _own_label
from aperix_geo.services.analysis._labels import rank_labels as _rank_labels
from aperix_geo.services.analysis._query import responses_in_window as _responses_in_window
from aperix_geo.services.analysis._series import (
    VISIBILITY_CHART_LABEL_LIMIT,
    TOPIC_VISIBILITY_RANK_LIMIT,
    align_previous_daily_to_current as _align_previous_daily_to_current,
    align_previous_single_series as _align_previous_single_series,
    top_visibility_labels as _top_visibility_labels,
)
from aperix_geo.services.analysis.citation import (
    build_citation_analysis,
    build_citation_brand_rank,
    build_citation_domain_analysis,
    build_citations,
)
from aperix_geo.services.analysis.diagnosis import build_diagnosis
from aperix_geo.services.analysis.entity import list_analysis_entities, resolve_analysis_entity
from aperix_geo.services.analysis.metrics import MetricsBundle
from aperix_geo.services.analysis.metrics_api import build_analysis_entities, build_unified_metrics
from aperix_geo.services.analysis.opportunity import (
    build_backlink_opportunities,
    build_content_opportunities,
    enterprise_domain_roots as _enterprise_domain_roots,
)
from aperix_geo.services.analysis.overview import build_overview
from aperix_geo.services.analysis.performance import (
    build_platform_performance,
    build_prompts_performance,
    build_topics_performance,
)
from aperix_geo.services.analysis.prompt_detail import build_prompt_detail_responses
from aperix_geo.services.analysis.platform import build_platform_matrix_analysis
from aperix_geo.services.analysis.rank import build_rank
from aperix_geo.services.analysis.sentiment import (
    build_daily_sentiment_series,
    build_sentiment_analysis,
)
from aperix_geo.services.analysis.visibility import (
    build_topic_visibility_ranks,
    build_visibility_analysis,
)

__all__ = [
    "MetricsBundle",
    "VISIBILITY_CHART_LABEL_LIMIT",
    "TOPIC_VISIBILITY_RANK_LIMIT",
    "build_overview",
    "build_rank",
    "build_topics_performance",
    "build_prompts_performance",
    "build_prompt_detail_responses",
    "build_citations",
    "build_topic_visibility_ranks",
    "build_visibility_analysis",
    "build_platform_performance",
    "build_platform_matrix_analysis",
    "build_citation_analysis",
    "build_citation_brand_rank",
    "build_citation_domain_analysis",
    "build_daily_sentiment_series",
    "build_sentiment_analysis",
    "build_content_opportunities",
    "build_backlink_opportunities",
    "build_diagnosis",
    "list_analysis_entities",
    "resolve_analysis_entity",
    "build_analysis_entities",
    "build_unified_metrics",
    # Legacy private aliases for tests
    "_responses_in_window",
    "_own_label",
    "_rank_labels",
    "_top_visibility_labels",
    "_align_previous_daily_to_current",
    "_align_previous_single_series",
    "_enterprise_domain_roots",
]
