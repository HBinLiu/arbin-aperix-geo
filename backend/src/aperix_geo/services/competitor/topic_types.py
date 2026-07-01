"""GEO 监测主题簇类型。"""

from __future__ import annotations

from typing import TypedDict

MAX_MONITORING_TOPICS = 5
MIN_TOPIC_NAME_LEN = 2
MAX_TOPIC_NAME_LEN = 12
MIN_SEED_QUERIES_PER_TOPIC = 3


class SeedQuery(TypedDict):
    text: str
    intent: str
    funnel: str
    decision: str


class TopicCluster(TypedDict):
    name: str
    seed_queries: list[SeedQuery]
