"""Prompt 探针标签 taxonomy：funnel / intent / decision 枚举与归一化。"""

from __future__ import annotations

from typing import Literal

FUNNEL_STAGES = frozenset({"tofu", "mofu", "bofu"})
SEARCH_INTENTS = frozenset({"informational", "commercial", "transactional"})
DECISION_TYPES = frozenset(
    {
        "category_awareness",
        "solution_comparison",
        "trust_risk",
        "price_value",
        "scenario_fit",
    }
)

DecisionType = Literal[
    "category_awareness",
    "solution_comparison",
    "trust_risk",
    "price_value",
    "scenario_fit",
]

DEFAULT_FUNNEL_STAGE = "mofu"
DEFAULT_SEARCH_INTENT = "commercial"
DEFAULT_DECISION_TYPE = "category_awareness"

DECISION_TYPE_LABELS: dict[str, str] = {
    "category_awareness": "品类认知",
    "scenario_fit": "场景适配",
    "solution_comparison": "选型对比",
    "trust_risk": "信任与风险",
    "price_value": "价格与性价比",
}


def normalize_funnel_stage(value: str | None) -> str:
    key = (value or "").strip().lower()
    return key if key in FUNNEL_STAGES else DEFAULT_FUNNEL_STAGE


def normalize_search_intent(value: str | None) -> str:
    key = (value or "").strip().lower()
    return key if key in SEARCH_INTENTS else DEFAULT_SEARCH_INTENT


def normalize_decision(value: str | None, *, default: str = "") -> str:
    """seed / LLM 字段 decision；default='' 时无效枚举返回空串。"""
    key = (value or "").strip().lower()
    return key if key in DECISION_TYPES else default


def normalize_decision_type(value: str | None) -> str:
    """Prompt ORM/API 字段 decision_type。"""
    return normalize_decision(value, default=DEFAULT_DECISION_TYPE)
