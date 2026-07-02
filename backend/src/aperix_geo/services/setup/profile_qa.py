"""微观利基画像词表质量校验（主题/提示词生成前门禁）。"""

from __future__ import annotations

from aperix_geo.services.competitor.profile import (
    MAX_LEXICON_TERMS,
    MAX_SEARCH_QUERIES,
    merge_profile_updates,
    search_queries_list,
    topic_lexicon_dict,
)
from aperix_geo.services.competitor.types import NicheProfile
from aperix_geo.services.setup.query_style import validate_search_queries_style
from aperix_geo.services.setup.keyword_plan import (
    MIN_CORE_KEYWORDS,
    MIN_LONG_TAIL_LEN,
    KeywordPlan,
    _compact_casefold,
    build_keyword_plan,
    dedupe_substring_terms,
    is_modifier_only_category_term,
    match_core_keyword,
    search_query_anchor_terms,
    select_topic_core_keywords,
)


def _compose_search_query(core: str, plan: KeywordPlan, *, index: int = 0) -> str:
    """用 profile 词表 modifiers 组合长尾问句（无硬编码后缀）。"""
    mods = plan["all_modifiers"]
    if not mods:
        return core
    m1 = mods[index % len(mods)]
    m2 = mods[(index + 1) % len(mods)] if len(mods) > 1 else m1
    q = f"{core}{m1}{m2}"
    if len(q) < MIN_LONG_TAIL_LEN:
        q = f"{core}{m1}"
    return q


def _synthesize_search_queries(plan: KeywordPlan) -> list[str]:
    core = plan["core_keywords"]
    out: list[str] = []
    for i, term in enumerate(core[:MAX_SEARCH_QUERIES]):
        out.append(_compose_search_query(term, plan, index=i))
    return out


def repair_profile_search_queries(profile: NicheProfile) -> NicheProfile:
    """LLM 长尾词漂移时：前缀补核心词或按 core+modifier 模板重写。"""
    plan = build_keyword_plan(profile)
    core = plan["core_keywords"]
    if len(core) < MIN_CORE_KEYWORDS:
        return profile

    anchors = search_query_anchor_terms(profile)
    primary = max(core, key=len)
    repaired: list[str] = []

    for q in search_queries_list(profile):
        text = q.strip()
        if not text:
            continue
        if match_core_keyword(text, anchors):
            repaired.append(text)
            continue
        candidate = f"{primary}{text}"
        if match_core_keyword(candidate, anchors) and len(candidate) >= MIN_LONG_TAIL_LEN:
            repaired.append(candidate)
            continue
        repaired.append(_compose_search_query(primary, plan, index=len(repaired)))

    if not repaired:
        repaired = _synthesize_search_queries(plan)

    return merge_profile_updates(profile, search_queries=repaired[:MAX_SEARCH_QUERIES])


def sanitize_profile_lexicon(profile: NicheProfile) -> NicheProfile:
    """P0：category 去包含、泛词下沉到 scenario，必要时从 features 补 head 词。"""
    lexicon = topic_lexicon_dict(profile)
    scenario = list(lexicon.get("scenario_terms", []))
    audience = list(lexicon.get("audience_terms", []))
    pain = list(lexicon.get("pain_terms", []))
    kept_category: list[str] = []
    demoted: list[str] = []
    raw_categories = [t.strip() for t in lexicon.get("category_terms", []) if t.strip()]
    category_heads = dedupe_substring_terms(raw_categories)

    for term in lexicon.get("category_terms", []):
        text = term.strip()
        if not text:
            continue
        if text not in category_heads:
            demoted.append(text)
        elif is_modifier_only_category_term(text, profile=profile):
            demoted.append(text)
        else:
            kept_category.append(text)

    scenario = _dedupe_terms_local(demoted + scenario)
    kept_category = dedupe_substring_terms(kept_category)

    category_compact = {_compact_casefold(term) for term in kept_category}
    for raw in str(profile.get("features") or "").split("、"):
        feat = raw.strip()
        if not feat or is_modifier_only_category_term(feat, profile=profile):
            if feat and feat not in scenario:
                scenario.append(feat)
            continue
        fc = _compact_casefold(feat)
        if fc in category_compact:
            continue
        if any(fc in existing or existing in fc for existing in category_compact if existing):
            continue
        kept_category.append(feat)
        category_compact.add(fc)

    kept_category = dedupe_substring_terms(kept_category)

    return merge_profile_updates(
        profile,
        profile_patch={
            "category_terms": "、".join(kept_category[:MAX_LEXICON_TERMS]),
            "scenario_terms": "、".join(_dedupe_terms_local(scenario)[:MAX_LEXICON_TERMS]),
            "audience_terms": "、".join(_dedupe_terms_local(audience)[:MAX_LEXICON_TERMS]),
            "pain_terms": "、".join(_dedupe_terms_local(pain)[:MAX_LEXICON_TERMS]),
        },
    )


def _dedupe_terms_local(terms: list[str]) -> list[str]:
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


def validate_profile_lexicon(profile: NicheProfile) -> None:
    """确保 profile 具备可用的核心词与长尾问句范例。"""
    plan = build_keyword_plan(profile)
    usable_cores = select_topic_core_keywords(profile, count=MIN_CORE_KEYWORDS)
    if len(usable_cores) < MIN_CORE_KEYWORDS:
        raise ValueError(
            f"topic_lexicon 核心词不足：category_terms/features 至少提供 {MIN_CORE_KEYWORDS} 条"
            f"可绑定 topic 的具体核心词，当前 {len(usable_cores)} 条"
        )

    long_tails = plan["long_tail_examples"]
    if not long_tails:
        raise ValueError("search_queries 不能为空，须提供 4–5 条长尾检索范例")

    anchors = search_query_anchor_terms(profile)
    for query in long_tails:
        q = query.strip()
        if len(q) < MIN_LONG_TAIL_LEN:
            raise ValueError(f"search_queries 每条须 ≥{MIN_LONG_TAIL_LEN} 字：{q}")
        if not match_core_keyword(q, anchors):
            raise ValueError(f"search_queries 须含至少 1 个核心词：{q}")

    validate_search_queries_style(long_tails, plan=plan)

    if not plan["all_modifiers"]:
        raise ValueError(
            "topic_lexicon 须提供 scenario/audience/pain 修饰词，用于长尾问句组合"
        )
