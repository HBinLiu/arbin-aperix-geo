"""topic_plan LLM 响应解析。"""

from __future__ import annotations

from typing import Any

from aperix_geo.services.competitor.topic_types import MAX_MONITORING_TOPICS, TopicCluster
from aperix_geo.services.setup.topic_seed import parse_seed


def parse_topic_plan_response(data: dict[str, Any]) -> list[TopicCluster]:
    """topic_plan LLM JSON → TopicCluster 列表（仅结构解析 + seed 归一化）。"""
    raw = data.get("topic_clusters")
    if not isinstance(raw, list):
        return []

    out: list[TopicCluster] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        seeds_raw = item.get("seed_queries")
        seeds = []
        if isinstance(seeds_raw, list):
            for seed_raw in seeds_raw:
                seed = parse_seed(seed_raw)
                if seed is not None:
                    seeds.append(seed)
        out.append(TopicCluster(name=name, seed_queries=seeds))
    return out[:MAX_MONITORING_TOPICS]
