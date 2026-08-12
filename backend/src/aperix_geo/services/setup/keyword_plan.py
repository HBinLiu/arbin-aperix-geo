"""关键词架构：精简画像 keywords → core + 合成长尾范例（seed 兜底）。"""

from __future__ import annotations

import re
import unicodedata
from typing import TypedDict

from aperix_geo.services.competitor.profile import keywords_list
from aperix_geo.services.competitor.types import NicheProfile

MIN_LONG_TAIL_LEN = 8

# 每 core 合成 5 条，对齐 PROMPT_PER_TOPIC，供 gap-fill / LLM 失败兜底
_LONG_TAIL_TEMPLATES: tuple[str, ...] = (
    "{core}怎么选合适",
    "{core}如何选择方案",
    "如何评估{core}",
    "{core}和同类方案怎么比",
    "{core}价格和性价比如何",
)


class KeywordPlan(TypedDict):
    core_keywords: list[str]
    long_tail_examples: list[str]


def is_broad_lexicon_term(term: str, profile: NicheProfile) -> bool:
    """过宽词根：等同 company，或等同 industry 且不在 keywords。"""
    text = term.strip()
    if len(text) < 2:
        return True
    cf = text.casefold()
    company = str(profile.get("company") or "").strip()
    if company and cf == company.casefold():
        return True
    industry = str(profile.get("industry") or "").strip()
    if industry and industry != "未知行业" and cf == industry.casefold():
        category = {t.strip().casefold() for t in keywords_list(profile) if t.strip()}
        if cf not in category:
            return True
    return False


def _compact_casefold(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text.strip())
    return re.sub(r"\s+", "", normalized).casefold()


def build_keyword_plan(profile: NicheProfile) -> KeywordPlan:
    """从精简画像 keywords 构建核心词，并按模板合成长尾范例。"""
    core: list[str] = []
    seen: set[str] = set()
    for term in keywords_list(profile):
        text = term.strip()
        if not text or is_broad_lexicon_term(text, profile):
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        core.append(text)

    long_tails: list[str] = []
    long_seen: set[str] = set()
    for c in core[:5]:
        for template in _LONG_TAIL_TEMPLATES:
            text = template.format(core=c).strip()
            if len(text) < MIN_LONG_TAIL_LEN:
                continue
            key = _compact_casefold(text)
            if key in long_seen:
                continue
            long_seen.add(key)
            long_tails.append(text)

    return KeywordPlan(core_keywords=core, long_tail_examples=long_tails)


def match_core_keyword(text: str, core_keywords: list[str]) -> str | None:
    """返回 text 中命中的最长核心词（完整子串；空格不敏感）。"""
    body = text.strip()
    if not body:
        return None
    body_cf = _compact_casefold(body)
    for kw in sorted(core_keywords, key=len, reverse=True):
        token = kw.strip()
        if token and _compact_casefold(token) in body_cf:
            return token
    return None


def resolve_topic_core_keyword(topic_name: str, plan: KeywordPlan) -> str | None:
    return match_core_keyword(topic_name, plan["core_keywords"])


def prompt_text_skeleton(text: str, *, core: str) -> str:
    """去掉 core 后的问句骨架（严格模式去重用）。"""
    body = _compact_casefold(text)
    core_cf = _compact_casefold(core)
    if core_cf and core_cf in body:
        body = body.replace(core_cf, "", 1)
    return body.strip()


def seed_candidates_from_plan(
    core: str,
    *,
    plan: KeywordPlan,
    max_len: int = 28,
) -> list[str]:
    """从合成长尾范例筛含本主题 core 的候选。"""
    if not core.strip():
        return []
    out: list[str] = []
    seen: set[str] = set()
    for raw in plan["long_tail_examples"]:
        text = raw.strip()[:max_len]
        if len(text) < MIN_LONG_TAIL_LEN:
            continue
        if not match_core_keyword(text, [core]):
            continue
        key = _compact_casefold(text)
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out
