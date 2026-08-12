"""主体 Markdown 摘要：模板生成与竞品章节回写。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.providers.prompts import (
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
    empty = "* **暂无：** 尚未添加竞品"
    return "\n".join(lines) if lines else empty


def merge_competitors_into_summary(
    summary: str | None,
    *,
    subject_type: str,
    competitors: list[dict[str, Any]] | None = None,
) -> str:
    del subject_type  # 竞品章节格式 domain/brand 模式共用
    body = _format_competitor_section_body(competitors=competitors)
    base = (summary or "").strip()
    if not base:
        return f"## {_COMPETITOR_HEADING}\n{body}\n"
    return replace_summary_section(base, _COMPETITOR_HEADING, body).rstrip() + "\n"


def generate_niche_profile_via_llm(
    *,
    entity_key: str,
    user_payload: dict[str, Any],
    temperature: float = 0.15,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Setup discover：精简微观利基结构化画像。"""
    text, usage, latency_ms = chat_completion(
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
    logger.debug(
        "Setup 微观利基画像 LLM: entity=%r (%dms)",
        entity_key,
        latency_ms,
    )
    return data, usage


def merge_llm_usage(*usages: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for usage in usages:
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            merged[key] = int(merged.get(key) or 0) + int(usage.get(key) or 0)
    return merged


def fallback_profile_summary(profile: NicheProfile, *, entity: str, region_label: str) -> str:
    name = profile.get("company") or entity
    industry = profile.get("industry") or "—"
    keywords = str(profile.get("keywords") or "").strip() or "—"
    brief = str(profile.get("brief") or "").strip() or "—"
    return (
        f"# {name}\n\n"
        f"## 概述\n{name} 定位于「{industry}」。{brief}\n\n"
        f"## 核心能力\n* **监测关键词：** {keywords}\n\n"
        f"## 产品与服务\n* **待补充：** 可在主体详情中完善\n\n"
        f"## 目标用户\n* **说明：** {brief}\n\n"
        f"## 市场定位\n* **定位：** 在 {industry} 垂直赛道提供差异化方案\n\n"
        f"## 竞品\n* **待补充：** 见竞品章节\n\n"
        f"## 核心价值\n在 {industry} 领域围绕「{keywords}」开展监测。\n\n"
        f"## 独家能力\n* **关键词：** {keywords}\n\n"
        f"## 客户痛点\n* **待明确：** 需结合业务补充\n\n"
        f"## 理想客户画像\n{brief}\n\n"
        f"## 决策触发点\n「{industry} 有哪些合适方案？」\n\n"
        f"## 地域与合规\n* **主要市场：** {region_label}\n"
        f"* **合规要求：** 待补充"
    )
