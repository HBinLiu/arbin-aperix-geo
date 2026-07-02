"""Prompt 探针标签 taxonomy：funnel / intent / decision 枚举与归一化。"""

from __future__ import annotations

from dataclasses import dataclass
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

FUNNEL_STAGE_LABELS: dict[str, str] = {
    "tofu": "认知期",
    "mofu": "考虑期",
    "bofu": "决策期",
}

SEARCH_INTENT_LABELS: dict[str, str] = {
    "informational": "了解型",
    "commercial": "对比型",
    "transactional": "交易型",
}

DECISION_TYPE_LABELS: dict[str, str] = {
    "category_awareness": "品类认知",
    "scenario_fit": "场景适配",
    "solution_comparison": "选型对比",
    "trust_risk": "信任与风险",
    "price_value": "价格与性价比",
}


@dataclass(frozen=True)
class TaxonomyOption:
    value: str
    label: str


@dataclass(frozen=True)
class PromptTaxonomyMeta:
    funnel_stages: tuple[TaxonomyOption, ...]
    search_intents: tuple[TaxonomyOption, ...]
    decision_types: tuple[TaxonomyOption, ...]
    default_funnel_stage: str
    default_search_intent: str
    default_decision_type: str


def _options(values: frozenset[str], labels: dict[str, str]) -> tuple[TaxonomyOption, ...]:
    ordered = sorted(values)
    return tuple(TaxonomyOption(value=key, label=labels.get(key, key)) for key in ordered)


def prompt_taxonomy_meta() -> PromptTaxonomyMeta:
    """前端下拉与表格展示用的 taxonomy 元数据。"""
    return PromptTaxonomyMeta(
        funnel_stages=_options(FUNNEL_STAGES, FUNNEL_STAGE_LABELS),
        search_intents=_options(SEARCH_INTENTS, SEARCH_INTENT_LABELS),
        decision_types=_options(DECISION_TYPES, DECISION_TYPE_LABELS),
        default_funnel_stage=DEFAULT_FUNNEL_STAGE,
        default_search_intent=DEFAULT_SEARCH_INTENT,
        default_decision_type=DEFAULT_DECISION_TYPE,
    )


def funnel_stage_label(value: str | None) -> str:
    key = (value or "").strip().lower()
    return FUNNEL_STAGE_LABELS.get(key, key)


def search_intent_label(value: str | None) -> str:
    key = (value or "").strip().lower()
    return SEARCH_INTENT_LABELS.get(key, key)


def decision_type_label(value: str | None) -> str:
    key = (value or "").strip().lower()
    return DECISION_TYPE_LABELS.get(key, key)


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


@dataclass(frozen=True)
class PromptTaxonomyLock:
    """生成提示词时固定 funnel / intent / decision。"""

    funnel_stage: str
    search_intent: str
    decision_type: str

    def to_llm_payload(self) -> dict[str, str]:
        return {
            "funnel": self.funnel_stage,
            "intent": self.search_intent,
            "decision": self.decision_type,
        }

    def apply_prompt_row(self, row: dict[str, str]) -> dict[str, str]:
        return {
            **row,
            "funnel_stage": self.funnel_stage,
            "search_intent": self.search_intent,
            "decision_type": self.decision_type,
        }


def prompt_taxonomy_lock(
    *,
    funnel_stage: str | None,
    search_intent: str | None,
    decision_type: str | None,
) -> PromptTaxonomyLock:
    return PromptTaxonomyLock(
        funnel_stage=normalize_funnel_stage(funnel_stage),
        search_intent=normalize_search_intent(search_intent),
        decision_type=normalize_decision_type(decision_type),
    )
