"""Read-time aggregates for MVP dashboards."""

from __future__ import annotations

from aperix_geo.services.analysis._labels import own_label as _own_label
from aperix_geo.services.analysis._labels import rank_labels as _rank_labels
from aperix_geo.services.analysis._parsed import (
    cited_competitor_on_source as _cited_competitor_on_source,
)
from aperix_geo.services.analysis._parsed import has_own_domain_link as _has_own_domain_link
from aperix_geo.services.analysis._parsed import mentions_own as _mentions_own
from aperix_geo.services.analysis._parsed import parsed_sentiment_score as _parsed_sentiment_score
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
    citation_share_from_rows as _citation_share_from_rows,
)
from aperix_geo.services.analysis.diagnosis import build_diagnosis
from aperix_geo.services.analysis.metrics import MetricsBundle, compute_subject_metrics
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
from aperix_geo.services.analysis.rank import build_rank, rank_from_rows as _rank_from_rows
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
    "compute_subject_metrics",
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
    # Legacy private aliases for tests
    "_mentions_own",
    "_has_own_domain_link",
    "_cited_competitor_on_source",
    "_responses_in_window",
    "_parsed_sentiment_score",
    "_own_label",
    "_rank_labels",
    "_rank_from_rows",
    "_citation_share_from_rows",
    "_top_visibility_labels",
    "_align_previous_daily_to_current",
    "_align_previous_single_series",
    "_enterprise_domain_roots",
]
