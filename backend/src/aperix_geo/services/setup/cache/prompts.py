"""Setup UI Step 2→3：提示词 generation hash 与 session 缓存读取。"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from aperix_geo.services.prompts.setup import PROMPT_PER_TOPIC


def prompts_generation_hash(
    *,
    entity: str,
    topics: list[str],
    competitors: list[str],
    industry: str,
    features: str,
    customers: str,
    aliases: list[str],
    exclude_prompts: list[str],
    prompts_per_topic: int = PROMPT_PER_TOPIC,
) -> str:
    payload = {
        "entity": entity.strip(),
        "topics": sorted(t.strip() for t in topics if t.strip()),
        "competitors": sorted(c.strip() for c in competitors if c.strip()),
        "industry": industry.strip(),
        "features": features.strip(),
        "customers": customers.strip(),
        "aliases": sorted(a.strip() for a in aliases if a.strip()),
        "exclude_prompts": sorted(p.strip() for p in exclude_prompts if p.strip()),
        "prompts_per_topic": prompts_per_topic,
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
