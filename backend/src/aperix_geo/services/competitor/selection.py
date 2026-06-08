"""从交叉验算结果生成竞品短名单（仅及格分 + 分数排序）。"""

from __future__ import annotations

import logging

from aperix_geo.config import get_settings
from aperix_geo.services.competitor.cross_validate import expand_ranked_domains
from aperix_geo.utils.domains import is_valid_hostname, strip_hostname
from aperix_geo.services.competitor.types import CrossValidateResult, NicheProfile, SearchPool
from aperix_geo.services.providers.prompts import (
    COMPETITOR_BRAND_SELECTION_SYSTEM,
    brand_selection_user_content,
)
from aperix_geo.services.providers import chat_completion
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)

_REGION_LABELS = {"CN": "中国大陆", "HK": "中国香港", "TW": "中国台湾"}


def _format_search_block(pool: SearchPool) -> str:
    lines: list[str] = []
    for idx, hit in enumerate(pool.hits[:20], start=1):
        title = (hit.title or "（无标题）")[:120]
        snippet = (hit.snippet or "（无摘要）")[:220]
        url = (hit.url or "")[:200]
        lines.append(f"{idx}. {title}\n   摘要：{snippet}\n   来源：{url or '—'}")
    return "\n".join(lines)


def select_domain_shortlist(
    profile: NicheProfile,
    *,
    target_domain: str,
    pool: SearchPool,
    validation: CrossValidateResult,
    region: str,
) -> list[str]:
    """仅分数 >= COMPETITOR_MIN_SCORE 的域名，按得分降序，最多 RESULT_MAX 个。"""
    del profile, target_domain, pool, region  # 保留签名供 pipeline / 测试兼容
    settings = get_settings()
    from aperix_geo.services.competitor.defaults import RESULT_MAX

    return expand_ranked_domains(
        validation,
        min_score=settings.competitor_min_score,
        max_keep=RESULT_MAX,
        heads=validation.heads,
    )


def select_brand_names(
    profile: NicheProfile,
    *,
    brand: str,
    pool: SearchPool,
    region: str,
    language: str,
) -> list[str]:
    from aperix_geo.services.competitor.defaults import RESULT_MAX

    if not pool.hits:
        logger.warning("品牌模式竞品筛选：无搜索结果，跳过 LLM 抽取")
        return []

    region_label = _REGION_LABELS.get(region, region)
    messages = [
        {"role": "system", "content": COMPETITOR_BRAND_SELECTION_SYSTEM},
        {
            "role": "user",
            "content": brand_selection_user_content(
                brand=brand,
                profile=profile,
                region_label=region_label,
                language=language,
                search_block=_format_search_block(pool),
                max_brands=RESULT_MAX,
            ),
        },
    ]
    text, _, _ = chat_completion(messages, temperature=0.2, json_mode=True)
    out: list[str] = []
    for item in extract_json_object(text).get("brand_names") or []:
        name = str(item).strip()
        if not name or len(name) > 120:
            continue
        if is_valid_hostname(strip_hostname(name)):
            continue
        out.append(name)
    return list(dict.fromkeys(out))
