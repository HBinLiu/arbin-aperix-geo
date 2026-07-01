"""SEO 式关键词架构：核心词 + 修饰词 + 长尾范例（贯穿 profile → topic → prompt）。"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, TypedDict

from aperix_geo.services.competitor.profile import search_queries_list, topic_lexicon_dict
from aperix_geo.services.competitor.types import NicheProfile

MIN_CORE_KEYWORDS = 3
MIN_TOPIC_CORE_KEYWORDS = 5
MIN_LONG_TAIL_LEN = 8


def is_broad_lexicon_term(term: str, profile: NicheProfile) -> bool:
    """过宽词根：等同 company，或等同 industry 且不在 category_terms。"""
    text = term.strip()
    if len(text) < 2:
        return True
    cf = text.casefold()
    company = str(profile.get("company") or "").strip()
    if company and cf == company.casefold():
        return True
    industry = str(profile.get("industry") or "").strip()
    if industry and industry != "未知行业" and cf == industry.casefold():
        category = [
            t.strip().casefold()
            for t in topic_lexicon_dict(profile).get("category_terms", [])
            if t.strip()
        ]
        if cf not in category:
            return True
    return False


class KeywordPlan(TypedDict):
    core_keywords: list[str]
    modifiers: dict[str, list[str]]
    all_modifiers: list[str]
    long_tail_examples: list[str]


def _dedupe_terms(terms: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in terms:
        text = raw.strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def build_keyword_plan(profile: NicheProfile) -> KeywordPlan:
    """从 niche_profile 构建核心词表（category + features，去宽去重）。"""
    lexicon = topic_lexicon_dict(profile)
    core: list[str] = []
    seen: set[str] = set()

    for term in lexicon.get("category_terms", []):
        text = term.strip()
        if not text or is_broad_lexicon_term(text, profile):
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        core.append(text)

    for raw in str(profile.get("features") or "").split("、"):
        text = raw.strip()
        if not text or is_broad_lexicon_term(text, profile):
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        core.append(text)

    modifiers = {
        "scenario": _dedupe_terms(lexicon.get("scenario_terms", [])),
        "audience": _dedupe_terms(lexicon.get("audience_terms", [])),
        "pain": _dedupe_terms(lexicon.get("pain_terms", [])),
    }
    all_modifiers = _dedupe_terms(
        modifiers["scenario"] + modifiers["audience"] + modifiers["pain"]
    )

    return KeywordPlan(
        core_keywords=core,
        modifiers=modifiers,
        all_modifiers=all_modifiers,
        long_tail_examples=search_queries_list(profile),
    )


def keyword_plan_to_dict(plan: KeywordPlan) -> dict[str, Any]:
    return {
        "core_keywords": list(plan["core_keywords"]),
        "modifiers": {k: list(v) for k, v in plan["modifiers"].items()},
        "all_modifiers": list(plan["all_modifiers"]),
        "long_tail_examples": list(plan["long_tail_examples"]),
    }


def _compact_casefold(text: str) -> str:
    """匹配用：NFKC + 去空格 + casefold（兼容全角字符与「AI 可见度」/「AI可见度」）。"""
    normalized = unicodedata.normalize("NFKC", text.strip())
    return re.sub(r"\s+", "", normalized).casefold()


def _term_anchors_search_query(term: str, *, cores: list[str], long_tails: list[str]) -> bool:
    """term 是否在任一条 search_query 中作为最长核心词锚点出现。"""
    term_cf = _compact_casefold(term)
    if not term_cf:
        return False
    anchor_cores = dedupe_substring_terms(cores)
    for query in long_tails:
        q_cf = _compact_casefold(query)
        if term_cf not in q_cf:
            continue
        winner = match_core_keyword(query, anchor_cores)
        if winner and _compact_casefold(winner) == term_cf:
            return True
    return False


def is_modifier_only_category_term(
    term: str,
    *,
    profile: NicheProfile | None = None,
) -> bool:
    """仅适合作修饰词：依据 profile 词表分区与 search_queries 锚点，不用硬编码词表。"""
    text = re.sub(r"\s+", "", term.strip())
    if len(text) < 2:
        return True
    if profile is None:
        return False

    lexicon = topic_lexicon_dict(profile)
    modifier_pool = _dedupe_terms(
        list(lexicon.get("scenario_terms", []))
        + list(lexicon.get("audience_terms", []))
        + list(lexicon.get("pain_terms", []))
    )
    term_cf = _compact_casefold(text)
    if term_cf in {_compact_casefold(m) for m in modifier_pool}:
        return True

    category_terms = _dedupe_terms(
        [t.strip() for t in lexicon.get("category_terms", []) if t.strip()]
    )
    deduped_heads = dedupe_substring_terms(category_terms)

    plan = build_keyword_plan(profile)
    cores = plan["core_keywords"]
    long_tails = plan["long_tail_examples"]
    anchor_cores = dedupe_substring_terms(cores)
    features = [
        t.strip()
        for t in str(profile.get("features") or "").split("、")
        if t.strip()
    ]

    if _term_anchors_search_query(text, cores=anchor_cores, long_tails=long_tails):
        return False

    appears_in_tail = any(term_cf in _compact_casefold(q) for q in long_tails)
    if appears_in_tail:
        for query in long_tails:
            q_cf = _compact_casefold(query)
            if term_cf not in q_cf:
                continue
            winner = match_core_keyword(query, anchor_cores)
            if winner and _compact_casefold(winner) != term_cf:
                return True
            if not winner and text not in category_terms:
                return True
        return False

    anchored_heads = {
        _compact_casefold(c)
        for c in deduped_heads
        if _term_anchors_search_query(c, cores=anchor_cores, long_tails=long_tails)
    }
    if text in category_terms and term_cf not in anchored_heads and anchored_heads:
        if text in features or text in deduped_heads:
            peer_lens = [len(_compact_casefold(c)) for c in deduped_heads]
            if text in features:
                return False
            if len(term_cf) <= min(peer_lens):
                return True
        return False

    for mod in modifier_pool:
        mod_cf = _compact_casefold(mod)
        if mod_cf and (term_cf in mod_cf or mod_cf in term_cf):
            return True

    return False


def dedupe_substring_terms(terms: list[str]) -> list[str]:
    """去包含：较短词是较长词真子串时丢弃较短项。"""
    cleaned = _dedupe_terms(terms)
    drop: set[str] = set()
    compact = [(term, _compact_casefold(term)) for term in cleaned]
    for i, (_, ac) in enumerate(compact):
        if len(ac) < 2:
            drop.add(ac)
            continue
        for j, (_, bc) in enumerate(compact):
            if i == j or len(bc) < 2:
                continue
            if ac in bc and ac != bc and len(ac) < len(bc):
                drop.add(ac)
    return [term for term, ac in compact if ac not in drop]


def select_topic_core_keywords(
    profile: NicheProfile,
    *,
    count: int = MIN_TOPIC_CORE_KEYWORDS,
) -> list[str]:
    """Topic 步 deterministic 绑定的核心词列表（去重、去包含、过滤泛词）。"""
    plan = build_keyword_plan(profile)
    cores = dedupe_substring_terms(plan["core_keywords"])
    return [
        term for term in cores if not is_modifier_only_category_term(term, profile=profile)
    ][:count]


def search_query_anchor_terms(profile: NicheProfile) -> list[str]:
    """search_queries 校验锚点：核心词 + 原始 category + features（比 core_keywords 更宽）。"""
    plan = build_keyword_plan(profile)
    lexicon = topic_lexicon_dict(profile)
    raw_features = [t.strip() for t in str(profile.get("features") or "").split("、") if t.strip()]
    return _dedupe_terms(
        plan["core_keywords"]
        + list(lexicon.get("category_terms", []))
        + raw_features
    )


def match_core_keyword(text: str, core_keywords: list[str]) -> str | None:
    """返回 text 中命中的最长核心词（完整子串；空格不敏感）。"""
    body = text.strip()
    if not body:
        return None
    body_cf = _compact_casefold(body)
    matched: str | None = None
    for kw in sorted(core_keywords, key=len, reverse=True):
        token = kw.strip()
        if token and _compact_casefold(token) in body_cf:
            matched = token
            break
    return matched


def match_modifier(text: str, modifiers: list[str]) -> str | None:
    """返回 text 中命中的修饰词（完整子串）。"""
    return match_core_keyword(text, modifiers)


def resolve_topic_core_keyword(topic_name: str, plan: KeywordPlan) -> str | None:
    return match_core_keyword(topic_name, plan["core_keywords"])


def topic_modifiers_for_core(
    core: str,
    *,
    plan: KeywordPlan,
    topic_index: int = 0,
) -> list[str]:
    """为单个 core 分配优先修饰词（长尾范例 + 按 topic 错开 scenario/audience/pain）。"""
    pools = [
        plan["modifiers"]["scenario"],
        plan["modifiers"]["audience"],
        plan["modifiers"]["pain"],
    ]
    picked: list[str] = []

    for example in plan["long_tail_examples"]:
        if not match_core_keyword(example, [core]):
            continue
        for modifier in plan["all_modifiers"]:
            if modifier and match_modifier(example, [modifier]):
                key = modifier.casefold()
                if key not in {m.casefold() for m in picked}:
                    picked.append(modifier)

    for offset in range(3):
        pool = pools[(topic_index + offset) % 3]
        if not pool:
            continue
        choice = pool[(topic_index + offset) % len(pool)]
        key = choice.casefold()
        if key not in {m.casefold() for m in picked}:
            picked.append(choice)

    for modifier in plan["all_modifiers"]:
        key = modifier.casefold()
        if key not in {m.casefold() for m in picked}:
            picked.append(modifier)
    return picked


def prompt_text_skeleton(text: str, *, core: str, modifiers: list[str]) -> str:
    """去掉 core 与 modifiers 后的问句骨架，用于检测跨主题模板化。"""
    body = _compact_casefold(text)
    core_cf = _compact_casefold(core)
    if core_cf and core_cf in body:
        body = body.replace(core_cf, "", 1)
    for modifier in sorted(modifiers, key=len, reverse=True):
        token = _compact_casefold(modifier)
        if token:
            body = body.replace(token, "")
    return body.strip()


def build_topic_keyword_map(
    topics: list[str],
    *,
    plan: KeywordPlan,
) -> list[dict[str, Any]]:
    """为 Prompt/Topic 步生成 topic → core + 优先修饰词映射。"""
    rows: list[dict[str, Any]] = []
    for idx, topic in enumerate(topics):
        name = topic.strip()
        if not name:
            continue
        core = resolve_topic_core_keyword(name, plan) or ""
        preferred = topic_modifiers_for_core(core, plan=plan, topic_index=idx) if core else []
        rows.append(
            {
                "topic": name,
                "core_keyword": core,
                "preferred_modifiers": preferred[:4],
                "primary_modifiers": preferred[:3],
            }
        )
    return rows


def seed_candidates_from_plan(
    core: str,
    *,
    plan: KeywordPlan,
    preferred_modifiers: list[str] | None = None,
    topic_index: int = 0,
    max_len: int = 28,
) -> list[str]:
    """从 profile 长尾范例筛 seed 候选：须含本主题 core（profile 已校验锚点，不再二次要求修饰词）。"""
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
