"""主体 Markdown 摘要：生成、竞品回写、竞品搜索后 enrich。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.providers.prompts import (
    PROFILE_ENRICH_SECTION_HEADINGS,
    SUBJECT_PROFILE_ENRICH_SYSTEM,
    SUBJECT_PROFILE_SYSTEM,
    SUBJECT_PROFILE_USER_SUFFIX,
)
from aperix_geo.services.providers import chat_completion
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)

_COMPETITOR_HEADING = "竞品"
_COMPETITOR_HEADING_ALIASES = ("竞品", "Competitors")


def _competitor_section_pattern() -> re.Pattern[str]:
    aliases = "|".join(re.escape(h) for h in _COMPETITOR_HEADING_ALIASES)
    return re.compile(rf"(?m)^## ({aliases})\s*\n.*?(?=^## |\Z)", re.DOTALL)


def replace_summary_section(summary: str, heading: str, body: str) -> str:
    body = body.rstrip()
    section = f"## {heading}\n{body}\n\n"
    pattern = _competitor_section_pattern() if heading == _COMPETITOR_HEADING else re.compile(
        rf"(?m)^## {re.escape(heading)}\s*\n.*?(?=^## |\Z)",
        re.DOTALL,
    )
    if pattern.search(summary):
        return pattern.sub(section, summary, count=1)
    anchor = re.search(r"(?m)^## 核心价值\s*$", summary)
    if anchor:
        return summary[: anchor.start()] + section + summary[anchor.start() :]
    return summary.rstrip() + "\n\n" + section


def _format_competitor_section_body(
    *,
    competitors: list[dict[str, Any]] | None,
) -> str:
    lines: list[str] = []
    for item in competitors or []:
        domain = str(item.get("domain") or "").strip()
        brand = str(item.get("brand") or item.get("site_name") or domain).strip()
        summary = str(item.get("summary") or "").strip()
        if not brand and not domain:
            continue
        label = brand or domain
        suffix = f"（{domain}）" if domain and domain != brand else ""
        detail = f"：{summary}" if summary else "：同业竞品"
        lines.append(f"* **{label}**{suffix}{detail}")
    empty = "* **暂无：** 本轮搜索未发现符合条件的竞品"
    return "\n".join(lines) if lines else empty


def merge_competitors_into_summary(
    summary: str | None,
    *,
    subject_type: str,
    competitors: list[dict[str, Any]] | None = None,
) -> str:
    body = _format_competitor_section_body(competitors=competitors)
    base = (summary or "").strip()
    if not base:
        return f"## {_COMPETITOR_HEADING}\n{body}\n"
    return replace_summary_section(base, _COMPETITOR_HEADING, body).rstrip() + "\n"


def _apply_section_updates(summary: str, sections: dict[str, Any]) -> str:
    updated = summary
    for heading in PROFILE_ENRICH_SECTION_HEADINGS:
        body = str(sections.get(heading) or "").strip()
        if body:
            updated = replace_summary_section(updated, heading, body)
    return updated.rstrip() + "\n"


def enrich_profile_summary(
    summary: str | None,
    *,
    profile_fields: dict[str, str],
    subject_type: str,
    competitors: list[dict[str, Any]] | None,
    region_label: str,
    language_label: str,
) -> str:
    base = (summary or "").strip()
    if not base:
        return base

    competitor_context = []
    for i in competitors or []:
        brand = str(i.get("brand") or i.get("site_name") or "").strip()
        domain = str(i.get("domain") or "").strip()
        if brand or domain:
            competitor_context.append(f"{brand or domain} ({domain})".strip(" ()"))

    payload = {
        "subject_type": subject_type,
        "profile": profile_fields,
        "competitors": competitor_context,
        "current_summary_excerpt": base[:8000],
        "region": region_label,
        "language": language_label,
    }
    try:
        text, _, latency_ms = chat_completion(
            [
                {"role": "system", "content": SUBJECT_PROFILE_ENRICH_SYSTEM},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
            ],
            temperature=0.2,
            json_mode=True,
        )
        sections = extract_json_object(text).get("sections")
        if not isinstance(sections, dict):
            logger.warning("主体摘要 enrich: 无效 sections")
            return base
        enriched = _apply_section_updates(base, sections)
        logger.info(
            "主体摘要 enrich: sections=%s (%dms)",
            [k for k in PROFILE_ENRICH_SECTION_HEADINGS if str(sections.get(k) or "").strip()],
            latency_ms,
        )
        return enriched
    except Exception:
        logger.warning("主体摘要 enrich 失败", exc_info=True)
        return base


def finalize_profile_summary(
    summary: str | None,
    *,
    profile_fields: dict[str, str],
    subject_type: str,
    competitors: list[dict[str, Any]] | None,
    region_label: str,
    language_label: str,
) -> str:
    """竞品搜索后：回写竞品章节 + LLM enrich 其余难填章节。"""
    merged = merge_competitors_into_summary(
        summary,
        subject_type=subject_type,
        competitors=competitors,
    )
    return enrich_profile_summary(
        merged,
        profile_fields=profile_fields,
        subject_type=subject_type,
        competitors=competitors,
        region_label=region_label,
        language_label=language_label,
    )


def generate_profile_summary_via_llm(
    *,
    entity_key: str,
    user_payload: dict[str, Any],
    temperature: float = 0.15,
) -> tuple[dict[str, Any], str]:
    """调用 LLM，返回 (原始 JSON 对象, profile_summary)。"""
    text, _, latency_ms = chat_completion(
        [
            {"role": "system", "content": SUBJECT_PROFILE_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"{json.dumps(user_payload, ensure_ascii=False, indent=2)}\n\n"
                    f"{SUBJECT_PROFILE_USER_SUFFIX}"
                ),
            },
        ],
        temperature=temperature,
        json_mode=True,
    )
    data = extract_json_object(text)
    summary = str(data.get("profile_summary") or "").strip()
    logger.info(
        "主体画像 LLM: entity=%r mode=%s summary=%d chars (%dms)",
        entity_key,
        user_payload.get("mode"),
        len(summary),
        latency_ms,
    )
    return data, summary


def fallback_profile_summary(profile: NicheProfile, *, entity: str, region_label: str) -> str:
    name = profile.get("company") or entity
    features = profile.get("core_features") or "—"
    customers = profile.get("target_customers") or "—"
    industry = profile.get("industry") or "—"
    return (
        f"# {name}\n\n"
        f"## 概述\n{name} 是一家定位于「{industry}」领域的品牌/企业，主要服务 {customers}。\n\n"
        f"## 核心能力\n* **核心能力：** {features}\n\n"
        f"## 产品与服务\n* **待补充：** 需抓取产品/解决方案页面后完善\n\n"
        f"## 目标用户\n* **目标客户：** {customers}\n\n"
        f"## 市场定位\n* **待补充：** 待竞品对比分析后完善\n\n"
        f"## 竞品\n* **待补充：** 将在竞品搜索阶段完善\n\n"
        f"## 核心价值\n在 {industry} 领域提供 {features}。\n\n"
        f"## 独家能力\n* **待补充：** 待竞品对比分析后完善\n\n"
        f"## 客户痛点\n* **待补充：** 需结合行业调研\n\n"
        f"## 理想客户画像\n{industry} | 待补充 | 待补充。典型场景：{customers}\n\n"
        f"## 决策触发点\n「该方案能否满足 {customers} 在 {industry} 场景下的核心需求？」\n\n"
        f"## 地域与合规\n* **主要市场：** {region_label}\n"
        f"* **合规要求：** 待补充（需结合行业资质信息）"
    )
