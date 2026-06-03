"""主体 Markdown 摘要：生成、竞品回写、竞品搜索后 enrich。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.providers import chat_completion
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)

_COMPETITOR_HEADING = "竞品"
_COMPETITOR_HEADING_ALIASES = ("竞品", "Competitors")

_ENRICH_SECTION_HEADINGS = (
    "市场定位",
    "独家能力",
    "客户痛点",
    "理想客户画像",
    "决策触发点",
)

_MICRO_NICHE_FIELD_RULES = """【微观利基字段准则】：
1. industry：垂直细分赛道，禁止宏观词（如「医疗行业」「软件」）。
2. core_features：2–3 个核心技术/产品能力词或短语。
3. target_customers：精准付费或使用群体。
4. micro_keywords：4–5 个高特异性、可独立搜索、低歧义的硬核检索词。"""

_PROFILE_SUMMARY_STRUCTURE_ZH = """【profile_summary Markdown 结构】（二级标题必须严格使用下列中文，按顺序输出，不可省略或改用英文）：
# {品牌/公司主显示名}
## 概述
## 核心能力
4–6 条，格式为 * **标签：** 说明
## 产品与服务
3–5 条主要产品线/服务线/方案线
## 目标用户
3–5 条，格式为 * **用户群：** 场景说明
## 市场定位
## 竞品
公开信息不足时写 * **待补充：** 将在竞品搜索阶段完善
## 核心价值
## 独家能力
## 客户痛点
3 条（可结合行业常识推断）
## 理想客户画像
一行：行业 | 组织规模 | 决策角色。典型场景：…
## 决策触发点
一句引号包裹的典型采购/选型问题
## 地域与合规
* **主要市场：** …
* **合规要求：** …"""

_JSON_OUTPUT_RULES = """【硬性约束】：
- 必须且仅输出一个合法 JSON 对象，包含键：company, industry, core_features, target_customers, micro_keywords, profile_summary
- core_features 与 micro_keywords 为字符串数组；profile_summary 为完整 Markdown（换行用 \\n）
- 禁止 Markdown 代码块包裹 JSON；不确定处用谨慎表述；章节标题始终使用上述中文"""

_PROFILE_SYSTEM_PROMPT = f"""你是商业竞争情报专家。根据用户 message 中的调研材料，输出：
1) 结构化微观利基画像字段；
2) 完整 profile_summary Markdown。

{_MICRO_NICHE_FIELD_RULES}
- mode=domain：依据 site_data（homepage 与 extra_pages），严禁无依据捏造。
- mode=brand：优先依据 web_research；检索为空时再保守使用公开常识。

{_PROFILE_SUMMARY_STRUCTURE_ZH}

{_JSON_OUTPUT_RULES}"""

_ENRICH_SYSTEM_PROMPT = f"""你是商业竞争分析专家。根据微观利基画像、当前摘要与已确认竞品，**仅**重写以下章节正文（不含 ## 标题）：
{chr(10).join(f"- {h}" for h in _ENRICH_SECTION_HEADINGS)}

要求：市场定位/独家能力结合竞品做差异化；独家能力与客户痛点用 bullet；理想客户画像一行 ICP；决策触发点一句引号问句。
不要修改「竞品」章节。输出 JSON：{{"sections": {{"市场定位": "...", ...}}}}。"""


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
    subject_type: str,
    competitors: list[dict[str, Any]] | None,
    brand_names: list[str] | None,
) -> str:
    lines: list[str] = []
    if subject_type == "domain":
        for item in competitors or []:
            domain = str(item.get("domain") or "").strip()
            site_name = str(item.get("site_name") or domain).strip()
            if not site_name and not domain:
                continue
            label = site_name or domain
            if domain and domain != site_name:
                lines.append(f"* **{label}**（{domain}）：同业竞品")
            else:
                lines.append(f"* **{label}**：同业竞品")
        empty = "* **暂无：** 本轮搜索未发现符合条件的竞品"
    else:
        lines = [f"* **{n.strip()}**：同业竞品品牌" for n in (brand_names or []) if n.strip()]
        empty = "* **暂无：** 本轮搜索未发现符合条件的竞品品牌"
    return "\n".join(lines) if lines else empty


def merge_competitors_into_summary(
    summary: str | None,
    *,
    subject_type: str,
    competitors: list[dict[str, Any]] | None = None,
    brand_names: list[str] | None = None,
) -> str:
    body = _format_competitor_section_body(
        subject_type=subject_type,
        competitors=competitors,
        brand_names=brand_names,
    )
    base = (summary or "").strip()
    if not base:
        return f"## {_COMPETITOR_HEADING}\n{body}\n"
    return replace_summary_section(base, _COMPETITOR_HEADING, body).rstrip() + "\n"


def _apply_section_updates(summary: str, sections: dict[str, Any]) -> str:
    updated = summary
    for heading in _ENRICH_SECTION_HEADINGS:
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
    brand_names: list[str] | None,
    region_label: str,
    language_label: str,
) -> str:
    base = (summary or "").strip()
    if not base:
        return base

    if subject_type == "domain":
        competitor_context = [
            f"{str(i.get('site_name') or i.get('domain')).strip()} ({i.get('domain')})".strip(" ()")
            for i in (competitors or [])
            if i.get("domain") or i.get("site_name")
        ]
    else:
        competitor_context = [n.strip() for n in (brand_names or []) if n.strip()]

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
                {"role": "system", "content": _ENRICH_SYSTEM_PROMPT},
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
            [k for k in _ENRICH_SECTION_HEADINGS if str(sections.get(k) or "").strip()],
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
    brand_names: list[str] | None,
    region_label: str,
    language_label: str,
) -> str:
    """竞品搜索后：回写竞品章节 + LLM enrich 其余难填章节。"""
    merged = merge_competitors_into_summary(
        summary,
        subject_type=subject_type,
        competitors=competitors,
        brand_names=brand_names,
    )
    return enrich_profile_summary(
        merged,
        profile_fields=profile_fields,
        subject_type=subject_type,
        competitors=competitors,
        brand_names=brand_names,
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
            {"role": "system", "content": _PROFILE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"{json.dumps(user_payload, ensure_ascii=False, indent=2)}\n\n"
                    "请输出 JSON（含 profile_summary，章节标题使用中文）。"
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
