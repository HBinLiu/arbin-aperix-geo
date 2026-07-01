"""Setup 监测主题：API 载荷、LLM payload 与主题名归一化。"""

from __future__ import annotations

import re
from typing import Any

from aperix_geo.services.competitor.topic_types import MAX_MONITORING_TOPICS
from aperix_geo.services.setup.topic_seed import parse_seed, seed_to_llm_dict


def topic_name_key(name: str) -> str:
    """主题名比较键：去空白 + casefold（与 topic_qa 判重一致）。"""
    return re.sub(r"\s+", "", name.strip().casefold())


def cluster_topic_names(topic_clusters: list[Any] | None) -> list[str]:
    """从 topic_clusters 提取主题名列表（顺序保留）。"""
    names: list[str] = []
    for cluster in topic_clusters or []:
        if not isinstance(cluster, dict):
            continue
        name = str(cluster.get("name") or "").strip()
        if name:
            names.append(name)
    return names[:MAX_MONITORING_TOPICS]


def setup_topics_from_clusters(topic_clusters: list[Any] | None) -> list[dict[str, str]]:
    """topic_clusters → Setup API / 前端 TopicRow 载荷（纯业务靶心，仅 name）。"""
    return [{"name": name} for name in cluster_topic_names(topic_clusters)]


def cluster_to_llm_payload(cluster: dict[str, Any]) -> dict[str, Any]:
    """单簇 TopicCluster → Prompts 步 LLM user payload。"""
    name = str(cluster.get("name") or "").strip()
    seeds = []
    for raw in cluster.get("seed_queries") or []:
        seed = parse_seed(raw)
        if seed is not None:
            seeds.append(seed_to_llm_dict(seed))
    return {"name": name, "seed_queries": seeds}


def clusters_for_prompt_topics(
    topics: list[str],
    topic_clusters: list[Any] | None,
) -> list[dict[str, Any]]:
    """按用户确认主题顺序排列 topic_clusters，供 Prompts LLM 使用。"""
    by_name = {
        topic_name_key(str(c.get("name") or "")): cluster_to_llm_payload(c)
        for c in (topic_clusters or [])
        if isinstance(c, dict) and str(c.get("name") or "").strip()
    }
    if not by_name:
        return [{"name": topic, "seed_queries": []} for topic in topics]

    out: list[dict[str, Any]] = []
    for topic in topics:
        key = topic_name_key(topic)
        out.append(by_name.get(key) or {"name": topic, "seed_queries": []})
    return out
