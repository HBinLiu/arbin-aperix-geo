"""GEO 监测主题簇与候选问句类型。"""

from __future__ import annotations

from typing import Literal, TypedDict

DecisionType = Literal[
    "category_awareness",
    "solution_comparison",
    "trust_risk",
    "price_value",
    "scenario_fit",
]

DECISION_TYPES: frozenset[str] = frozenset(
    {
        "category_awareness",
        "solution_comparison",
        "trust_risk",
        "price_value",
        "scenario_fit",
    }
)

MAX_MONITORING_TOPICS = 5
MAX_TOPIC_NAME_LEN = 12
MIN_SEED_QUERIES_PER_TOPIC = 3
TARGET_CANDIDATE_QUERIES = 40


class SeedQuery(TypedDict):
    text: str
    intent: str
    funnel: str
    decision_type: str


class TopicCluster(TypedDict):
    name: str
    seed_queries: list[SeedQuery]


class CandidateQuery(TypedDict):
    text: str
    intent: str
    funnel: str
    decision_type: str
    seed_terms: list[str]
