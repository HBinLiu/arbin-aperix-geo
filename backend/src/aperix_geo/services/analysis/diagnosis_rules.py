"""Pure diagnosis priority and health-score rules (no DB or signal I/O)."""

from __future__ import annotations

from typing import Any

ACTION_PRIORITY_ORDER: dict[str, int] = {"high": 0, "medium": 1, "low": 2}


def mention_action_priority(mention_rate: float | None, average_rank: float | None) -> str:
    """AI 提及率行动优先级：衡量自有品牌绝对曝光健康度。"""
    issue = diagnosis_issue_type(mention_rate, average_rank)
    if issue == "not_mentioned":
        return "high"
    if issue in ("low_mention", "poor_rank"):
        return "medium"
    return "low"


def gap_action_priority(gap_rate: float) -> str:
    """品牌/来源差距行动优先级：衡量相对竞品落后程度。"""
    if gap_rate >= 0.8:
        return "high"
    if gap_rate >= 0.5:
        return "medium"
    return "low"


def mention_has_issue(mention_rate: float | None, average_rank: float | None) -> bool:
    """AI 提及率是否存在需行动的问题（非 healthy）。"""
    return mention_action_priority(mention_rate, average_rank) != "low"


def diagnosis_mention_rate(
    *,
    mention_own_count: int,
    mention_total_count: int,
    visibility_rate: float | None = None,
) -> float:
    """诊断口径 AI 提及率：被提及回复数 / 分析回复数（0~1，与表格副文案一致）。"""
    if visibility_rate is not None:
        return visibility_rate
    if mention_total_count <= 0:
        return 0.0
    return round(mention_own_count / mention_total_count, 4)


def has_diagnosis_content_gap(
    *,
    brand_gap_rate: float,
    source_gap_rate: float,
    mention_rate: float | None = None,
    average_rank: float | None = None,
    mention_priority: str | None = None,
) -> bool:
    """诊断内容表入表条件：品牌/来源差距，或 AI 提及率问题。"""
    if brand_gap_rate > 0 or source_gap_rate > 0:
        return True
    if mention_priority is not None:
        return mention_priority != "low"
    return mention_has_issue(mention_rate, average_rank)


def overall_action_priority(*priorities: str) -> str:
    """总优先级：取 AI 提及、品牌差距、来源差距行动优先级之最紧急者。"""
    return min(priorities, key=lambda key: ACTION_PRIORITY_ORDER.get(key, 9))


def diagnosis_issue_type(mention_rate: float | None, average_rank: float | None) -> str:
    rate = mention_rate or 0
    if rate <= 0:
        return "not_mentioned"
    if rate < 0.5:
        return "low_mention"
    if average_rank is not None and average_rank > 3:
        return "poor_rank"
    return "healthy"


def overall_diagnosis_status(score: float) -> str:
    if score >= 80:
        return "excellent"
    if score >= 60:
        return "good"
    if score >= 40:
        return "improvement"
    return "critical"


def health_score_from_gap(gap_rates: list[float]) -> float:
    """Average ``(1 - gap_rate)`` over the given rates (caller filters to gap > 0 prompts)."""
    if not gap_rates:
        return 0.0
    avg_gap = sum(gap_rates) / len(gap_rates)
    return round(max(0.0, (1 - avg_gap) * 100), 1)


def health_score_from_gap_items(items: list[dict[str, Any]], *, gap_key: str) -> float:
    """Health score for a gap dimension; denominator = prompts where ``gap_key > 0``."""
    gap_rates = [float(row[gap_key]) for row in items if float(row.get(gap_key) or 0) > 0]
    return health_score_from_gap(gap_rates)


def apply_diagnosis_row_priorities(item: dict[str, Any]) -> None:
    item["priority"] = overall_action_priority(
        item.get("mention_priority", "low"),
        item.get("brand_gap_priority", "low"),
        item.get("source_gap_priority", "low"),
    )


def refresh_gap_priorities(item: dict[str, Any]) -> None:
    item["brand_gap_priority"] = gap_action_priority(item["brand_gap_rate"])
    item["source_gap_priority"] = gap_action_priority(item["source_gap_rate"])
