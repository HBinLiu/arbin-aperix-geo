"""竞品发现诊断日志。"""

from __future__ import annotations

import logging

from aperix_geo.services.competitor.types import CandidateMeta

logger = logging.getLogger(__name__)


def competitor_log_prefix(
    *,
    round_idx: int | None = None,
    round_total: int | None = None,
) -> str:
    if round_idx is not None and round_total is not None:
        return f"竞品发现: 第{round_idx}/{round_total}轮 "
    return "竞品发现: "


def log_cross_validate_score(
    *,
    domain: str,
    score: float,
    reason: str,
    meta: CandidateMeta | None,
    reachable: bool | None = None,
    round_idx: int | None = None,
    round_total: int | None = None,
) -> None:
    prefix = competitor_log_prefix(round_idx=round_idx, round_total=round_total)
    url = (meta.website_url if meta else "") or "—"
    reach = ""
    if reachable is not None:
        reach = " 可打开" if reachable else " 不可打开"
    logger.info(
        "%s交叉验算 domain=%s score=%.1f url=%s%s %s",
        prefix,
        domain,
        score,
        url,
        reach,
        reason[:120],
    )
