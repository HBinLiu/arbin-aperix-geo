"""Setup 监测主题：API 载荷与主题名归一化（跨 steps / finalize / prompts 共用）。"""

from __future__ import annotations

import re
from typing import Any

from aperix_geo.services.competitor.topic_types import MAX_MONITORING_TOPICS


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
    out: list[dict[str, str]] = []
    for cluster in topic_clusters or []:
        if not isinstance(cluster, dict):
            continue
        name = str(cluster.get("name") or "").strip()
        if not name:
            continue
        out.append({"name": name})
    return out[:MAX_MONITORING_TOPICS]
