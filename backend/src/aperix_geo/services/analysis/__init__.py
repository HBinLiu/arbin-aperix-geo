"""Read-time aggregates for MVP dashboards."""

from __future__ import annotations

from aperix_geo.services.analysis._series import (
    VISIBILITY_CHART_LABEL_LIMIT,
    TOPIC_VISIBILITY_RANK_LIMIT,
)
from aperix_geo.services.analysis.citation import (
    build_citation_analysis,
    build_citation_domain_analysis,
    build_citation_domain_prompts_page,
    build_citation_domain_urls_page,
    build_citation_domains_page,
    build_citation_urls_page,
)
from aperix_geo.services.analysis.dashboard import build_dashboard_overview
from aperix_geo.services.analysis.diagnosis import (
    build_diagnosis_content,
    build_diagnosis_content_detail,
    build_diagnosis_content_summary,
)
from aperix_geo.services.analysis.entity import list_analysis_entities, resolve_analysis_entity
from aperix_geo.services.analysis.metrics import MetricsBundle, build_analysis_entities
from aperix_geo.services.analysis.opportunity import (
    build_backlink_opportunities,
    build_backlink_opportunity_detail,
    build_backlink_opportunity_prompts_page,
    build_backlink_opportunity_urls_page,
)
from aperix_geo.services.analysis.overview import build_overview
from aperix_geo.services.analysis.performance import (
    build_platform_performance,
    build_prompts_performance,
    build_prompts_performance_page,
    build_topics_performance,
)
from aperix_geo.services.analysis.prompt_detail import build_prompt_detail
from aperix_geo.services.analysis.platform import build_platform_analysis
from aperix_geo.services.analysis.rank import build_rank
from aperix_geo.services.analysis.responses import build_analysis_responses
from aperix_geo.services.analysis.sentiment import build_sentiment_analysis
from aperix_geo.services.analysis.visibility import (
    build_topic_visibility_ranks,
    build_visibility_analysis,
)

__all__ = [
    "MetricsBundle",
    "VISIBILITY_CHART_LABEL_LIMIT",
    "TOPIC_VISIBILITY_RANK_LIMIT",
    "build_overview",
    "build_dashboard_overview",
    "build_rank",
    "build_topics_performance",
    "build_prompts_performance",
    "build_prompts_performance_page",
    "build_prompt_detail",

    "build_topic_visibility_ranks",
    "build_visibility_analysis",
    "build_platform_performance",
    "build_platform_analysis",
    "build_citation_analysis",
    "build_citation_domain_analysis",
    "build_citation_domain_prompts_page",
    "build_citation_domain_urls_page",
    "build_citation_domains_page",
    "build_citation_urls_page",
    "build_sentiment_analysis",
    "build_analysis_responses",
    "build_diagnosis_content",
    "build_diagnosis_content_summary",
    "build_diagnosis_content_detail",
    "build_backlink_opportunities",
    "build_backlink_opportunity_detail",
    "build_backlink_opportunity_prompts_page",
    "build_backlink_opportunity_urls_page",
    "list_analysis_entities",
    "resolve_analysis_entity",
    "build_analysis_entities",
]
