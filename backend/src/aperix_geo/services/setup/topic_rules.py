"""监测主题规划共享规则（校验与 LLM guidance 单一来源）。"""

from __future__ import annotations

from typing import Any

from aperix_geo.services.competitor.profile import topic_lexicon_dict
from aperix_geo.services.setup.keyword_plan import build_keyword_plan
from aperix_geo.services.competitor.topic_types import (
    MAX_MONITORING_TOPICS,
    MAX_TOPIC_NAME_LEN,
    MIN_SEED_QUERIES_PER_TOPIC,
    MIN_TOPIC_NAME_LEN,
)
from aperix_geo.services.competitor.types import NicheProfile

MAX_SEEDS_PER_TOPIC = 8
MIN_SEED_TEXT_LEN = 8
MAX_SEED_TEXT_LEN = 28
MIN_CATEGORY_TOPIC_HITS = 5


def _clip_topic_name(text: str) -> str:
    return text.strip()[:MAX_TOPIC_NAME_LEN]


def _naming_examples(profile: NicheProfile) -> dict[str, list[str]]:
    """从当前画像动态生成命名正反例。"""
    lexicon = topic_lexicon_dict(profile)
    category = [t for t in lexicon.get("category_terms", []) if t.strip()]
    company = str(profile.get("company") or "").strip()
    industry = str(profile.get("industry") or "").strip()

    good: list[str] = []
    for cat in category[:3]:
        good.append(_clip_topic_name(cat))

    bad: list[str] = []
    if category:
        bad.append(_clip_topic_name(f"{category[0]}怎么选"))
    if company and category:
        bad.append(_clip_topic_name(f"{company}{category[0]}"))
    if industry and industry != "未知行业":
        bad.append(_clip_topic_name(f"{industry}保障"))

    return {
        "good_topic_names": good[:3],
        "bad_topic_names": bad[:3],
    }


def build_topic_plan_guidance(profile: NicheProfile) -> dict[str, Any]:
    """注入 user payload 的动态约束（数值、词表、命名示例）。"""
    plan = build_keyword_plan(profile)
    min_category_hits = min(MIN_CATEGORY_TOPIC_HITS, len(plan["core_keywords"])) if plan["core_keywords"] else 0

    return {
        "topic_count": MAX_MONITORING_TOPICS,
        "min_topic_name_len": MIN_TOPIC_NAME_LEN,
        "max_topic_name_len": MAX_TOPIC_NAME_LEN,
        "min_seeds_per_topic": MIN_SEED_QUERIES_PER_TOPIC,
        "max_seeds_per_topic": MAX_SEEDS_PER_TOPIC,
        "min_seed_text_len": MIN_SEED_TEXT_LEN,
        "max_seed_text_len": MAX_SEED_TEXT_LEN,
        "min_core_keyword_topics": min_category_hits,
        "core_keyword_coverage": "5 个 topic 各绑定 1 个不同 core_keyword（系统会按 keyword_plan 绑定 topic name）",
        "long_tail_examples": list(plan["long_tail_examples"]),
        "seed_style_rules": [
            "每个 topic 内 5 条 seed：decision 互异，去掉 core 与 modifiers 后句法骨架互异",
            "5 个 topic 之间禁止复用同一组固定句式，仅替换 core_keyword",
            "须从 long_tail_examples 分散仿写不同问法，勿复制同一套五句式",
            "像用户向 AI 随口提问；modifiers 自然嵌入，勿机械拼接 preferred_modifiers 原文",
        ],
        "forbidden_seed_shapes": [
            "禁止 5 个 topic 共用同一批固定句式（仅换 core）",
            "禁止同一 topic 内多条 seed 仅换 decision 而句法相同",
            "禁止对称排比式批量生成（前缀/后缀/疑问结构完全一致）",
        ],
        "anchor_lexicon_keys": [
            "category_terms",
            "scenario_terms",
            "audience_terms",
            "pain_terms",
            "features",
            "industry",
        ],
        "naming_rules": [
            f"topic name 由系统绑定为 core_keyword（{MIN_TOPIC_NAME_LEN}–{MAX_TOPIC_NAME_LEN} 字），LLM 重点输出 seed",
            "须完整包含 1 个 core_keyword（禁止仅靠片段匹配）",
            "5 条 topic 不得近重复（包含关系）且不得使用竞品对标/对比分析等泛词作 topic name",
            "不得含主体/竞品名与问句标记",
            f"同一 topic 至少 {MIN_SEED_QUERIES_PER_TOPIC} 条 seed，句法骨架互异优先于 decision 标签覆盖",
        ],
        **_naming_examples(profile),
    }
