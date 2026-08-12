"""Setup UI Step 2→3：提示词 generation hash 与 session 缓存读取。"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from aperix_geo.services.prompts.constants import PROMPT_PER_TOPIC
from aperix_geo.services.setup.topic_items import topic_name_key


def prompts_generation_hash(
    *,
    entity: str,
    topics: list[str],
    competitors: list[str],
    industry: str,
    keywords: str,
    brief: str,
    aliases: list[str],
    exclude_prompts: list[str],
    prompts_per_topic: int = PROMPT_PER_TOPIC,
) -> str:
    payload = {
        "entity": entity.strip(),
        # 用 topic_name_key，避免「AI 可见度」与「AI可见度」缓存分裂
        "topics": sorted({topic_name_key(t) for t in topics if t.strip()}),
        "competitors": sorted(c.strip() for c in competitors if c.strip()),
        "industry": industry.strip(),
        "keywords": keywords.strip(),
        "brief": brief.strip(),
        "aliases": sorted(a.strip() for a in aliases if a.strip()),
        "exclude_prompts": sorted(p.strip() for p in exclude_prompts if p.strip()),
        "prompts_per_topic": prompts_per_topic,
        "prompt_pipeline": "prompt_tags_v2",
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def cached_prompts(session: dict[str, Any], *, prompts_hash: str) -> list[dict[str, Any]] | None:
    if session.get("prompts_hash") != prompts_hash:
        return None
    cached = session.get("prompts_cache")
    if not isinstance(cached, list) or not cached:
        return None
    return cached
