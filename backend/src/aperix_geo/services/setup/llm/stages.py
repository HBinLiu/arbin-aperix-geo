"""Setup 向导 LLM 分步调用（discover 画像 / topics 模板摘要）。"""

from __future__ import annotations

import logging
from typing import Any

from aperix_geo.services.competitor.profile import keywords_list, normalize_niche_profile, region_label
from aperix_geo.services.competitor.summary import (
    fallback_profile_summary,
    generate_niche_profile_via_llm,
    merge_competitors_into_summary,
    merge_llm_usage,
)
from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.setup.llm.payloads import build_subject_research_payload

logger = logging.getLogger(__name__)

_MAX_PROFILE_ATTEMPTS = 2
_MIN_KEYWORDS = 1


def _validate_slim_profile(profile: NicheProfile) -> None:
    industry = str(profile.get("industry") or "").strip()
    if not industry or industry == "未知行业":
        raise ValueError("industry 无效")
    kws = keywords_list(profile)
    if len(kws) < _MIN_KEYWORDS:
        raise ValueError("keywords 至少 1 条")


def run_niche_profile_stage(
    *,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    website_url: str = "",
    user_corpus: str = "",
    homepage_text: str = "",
    homepage_metadata: dict[str, str] | None = None,
) -> tuple[NicheProfile, dict, dict[str, Any]]:
    """Setup discover：精简微观利基画像。"""
    target = target.strip()
    research_payload = build_subject_research_payload(
        subject_type=subject_type,
        target=target,
        region=region,
        language=language,
        website_url=website_url,
        user_corpus=user_corpus,
        homepage_text=homepage_text,
        homepage_metadata=homepage_metadata,
    )
    usage: dict[str, Any] = {}
    last_error: Exception | None = None
    validation_feedback: list[str] = []
    for attempt in range(_MAX_PROFILE_ATTEMPTS):
        user_payload = dict(research_payload)
        if validation_feedback:
            user_payload["validation_feedback"] = validation_feedback
        try:
            data, call_usage = generate_niche_profile_via_llm(
                entity_key=target,
                user_payload=user_payload,
            )
            usage = merge_llm_usage(usage, call_usage)
            profile = normalize_niche_profile(data, entity=target)
            _validate_slim_profile(profile)
        except ValueError as exc:
            last_error = exc
            validation_feedback = [str(exc)]
            logger.warning(
                "Setup 微观利基画像校验未通过 target=%r attempt=%d: %s",
                target,
                attempt + 1,
                exc,
            )
            continue

        return profile, research_payload, usage

    raise ValueError(f"微观利基画像失败：{last_error}") from last_error


def run_profile_summary_stage(
    *,
    profile: NicheProfile,
    subject_type: str,
    target: str,
    region: str,
    language: str,
    entity_key: str,
    competitors: list[dict[str, Any]] | None,
) -> tuple[str, dict[str, Any]]:
    """用户确认竞品后：模板摘要（含竞品，不含主题）。"""
    _ = (target, language)
    summary = fallback_profile_summary(
        profile,
        entity=entity_key,
        region_label=region_label(region),
    )
    summary = merge_competitors_into_summary(
        summary,
        subject_type=subject_type,
        competitors=competitors,
    )
    logger.info(
        "设置向导·主题·摘要 entity=%r 字数=%d 来源=fallback",
        entity_key,
        len(summary),
    )
    return summary, {}
