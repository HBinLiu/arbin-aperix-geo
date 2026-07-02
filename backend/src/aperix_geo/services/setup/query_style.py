"""监测问句结构校验（profile 驱动骨架互异；问法风格由 LLM 软评）。"""

from __future__ import annotations

from aperix_geo.services.setup.keyword_plan import (
    KeywordPlan,
    match_core_keyword,
    prompt_text_skeleton,
)

MIN_SKELETON_KINDS_PER_TOPIC = 4
MIN_SKELETON_LEN = 4


def search_query_skeletons(queries: list[str], *, plan: KeywordPlan) -> list[str]:
    """去掉 core/modifier 后的 search_query 骨架（用于互异校验）。"""
    cores = plan["core_keywords"]
    modifiers = plan["all_modifiers"]
    out: list[str] = []
    for raw in queries:
        text = raw.strip()
        if not text:
            continue
        core = match_core_keyword(text, cores) or ""
        if not core:
            continue
        sk = prompt_text_skeleton(text, core=core, modifiers=modifiers)
        if len(sk) >= MIN_SKELETON_LEN:
            out.append(sk)
    return out


def validate_search_queries_skeleton_diversity(queries: list[str], *, plan: KeywordPlan) -> None:
    """profile 长尾范例：去掉 core/modifier 后骨架须互异。"""
    cleaned = [q.strip() for q in queries if q.strip()]
    if len(cleaned) < 2:
        return
    skeletons = search_query_skeletons(cleaned, plan=plan)
    if len(skeletons) >= 2 and len(set(skeletons)) < len(skeletons):
        raise ValueError("search_queries 句法骨架重复，须去掉 core 与 modifiers 后互异")


def validate_search_queries_style(queries: list[str], *, plan: KeywordPlan) -> None:
    """Discover 长尾范例结构：骨架互异（问法风格见 query_style_llm）。"""
    validate_search_queries_skeleton_diversity(queries, plan=plan)
