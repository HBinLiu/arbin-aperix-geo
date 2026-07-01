"""Prompt decision_type 枚举与归一化。"""

from __future__ import annotations

from aperix_geo.services.competitor.topic_types import DECISION_TYPES

DEFAULT_DECISION_TYPE = ""

DECISION_TYPE_LABELS: dict[str, str] = {
    "category_awareness": "品类认知",
    "scenario_fit": "场景适配",
    "solution_comparison": "选型对比",
    "trust_risk": "信任与风险",
    "price_value": "价格与性价比",
}


def normalize_decision_type(value: str | None) -> str:
    key = (value or "").strip().lower()
    return key if key in DECISION_TYPES else DEFAULT_DECISION_TYPE


def decision_type_label(value: str | None) -> str:
    key = normalize_decision_type(value)
    if not key:
        return ""
    return DECISION_TYPE_LABELS.get(key, key)
