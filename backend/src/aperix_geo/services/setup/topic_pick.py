"""从 topic_lexicon 选定纯业务监测靶心（不含决策维度命名）。"""

from __future__ import annotations

from typing import Any

from aperix_geo.services.competitor.profile import topic_lexicon_dict
from aperix_geo.services.competitor.topic_types import MAX_MONITORING_TOPICS, MAX_TOPIC_NAME_LEN
from aperix_geo.services.competitor.types import NicheProfile


def parse_topic_names(data: dict[str, Any]) -> list[str]:
    raw = data.get("topic_names")
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        name = str(item or "").strip()
        if name:
            out.append(name)
    return out[:MAX_MONITORING_TOPICS]


def _trim_topic_name(name: str) -> str:
    text = name.strip()
    if len(text) <= MAX_TOPIC_NAME_LEN:
        return text
    return text[:MAX_TOPIC_NAME_LEN]


def _combine_name(*parts: str) -> str:
    merged = "".join(p.strip() for p in parts if p.strip())
    return _trim_topic_name(merged)


def fallback_topic_names_from_lexicon(profile: NicheProfile) -> list[str]:
    """LLM 失败时：从词表组合业务主题名（品类×场景优先）。"""
    lexicon = topic_lexicon_dict(profile)
    categories = [t.strip() for t in lexicon.get("category_terms", []) if len(t.strip()) >= 2]
    scenarios = [t.strip() for t in lexicon.get("scenario_terms", []) if len(t.strip()) >= 2]
    audiences = [t.strip() for t in lexicon.get("audience_terms", []) if len(t.strip()) >= 2]
    pains = [t.strip() for t in lexicon.get("pain_terms", []) if len(t.strip()) >= 2]

    names: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        key = name.casefold()
        if not name or key in seen or len(names) >= MAX_MONITORING_TOPICS:
            return
        seen.add(key)
        names.append(_trim_topic_name(name))

    for sc in scenarios:
        for cat in categories:
            add(_combine_name(sc, cat))
            if len(names) >= MAX_MONITORING_TOPICS:
                return names

    for cat in categories:
        add(_trim_topic_name(cat))
        if len(names) >= MAX_MONITORING_TOPICS:
            return names

    for aud in audiences:
        for cat in categories[:2]:
            add(_combine_name(aud, cat))
            if len(names) >= MAX_MONITORING_TOPICS:
                return names

    for pain in pains:
        for cat in categories[:2]:
            add(_combine_name(pain, cat))
            if len(names) >= MAX_MONITORING_TOPICS:
                return names

    for term in scenarios + audiences + categories + pains:
        add(_trim_topic_name(term))
        if len(names) >= MAX_MONITORING_TOPICS:
            break

    if len(names) < MAX_MONITORING_TOPICS:
        industry = str(profile.get("industry") or "").strip()
        if industry and industry != "未知行业":
            add(_trim_topic_name(industry))

    return names[:MAX_MONITORING_TOPICS]
