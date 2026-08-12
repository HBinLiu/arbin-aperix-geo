"""Setup 监测主题：名称归一化与 API 载荷。"""

from __future__ import annotations

import re
from typing import Any

from aperix_geo.services.competitor.topic_types import MAX_MONITORING_TOPICS


def topic_name_key(name: str) -> str:
    """主题名比较键：去空白 + casefold。"""
    return re.sub(r"\s+", "", name.strip().casefold())


def normalize_topic_names(raw: list[Any] | None, *, limit: int = MAX_MONITORING_TOPICS) -> list[str]:
    """去重保序的主题名列表。"""
    names: list[str] = []
    seen: set[str] = set()
    for item in raw or []:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
        else:
            name = str(item or "").strip()
        if not name:
            continue
        key = topic_name_key(name)
        if key in seen:
            continue
        seen.add(key)
        names.append(name)
        if len(names) >= limit:
            break
    return names


def setup_topics_from_names(names: list[str] | None) -> list[dict[str, str]]:
    """主题名 → Setup API / 前端 TopicRow 载荷。"""
    return [{"name": name} for name in normalize_topic_names(names)]
