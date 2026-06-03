"""从交叉验算结果生成竞品短名单（仅及格分 + 分数排序）。"""

from __future__ import annotations

import logging

from aperix_geo.config import get_settings
from aperix_geo.services.competitor.cross_validate import expand_ranked_domains
from aperix_geo.utils.domains import is_valid_hostname, strip_hostname
from aperix_geo.services.competitor.types import CrossValidateResult, NicheProfile, SearchPool
from aperix_geo.services.providers import chat_completion
from aperix_geo.utils.json import extract_json_object

logger = logging.getLogger(__name__)

_REGION_LABELS = {"CN": "中国大陆", "HK": "中国香港", "TW": "中国台湾"}


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
    region_label = _REGION_LABELS.get(region, region)
    if pool.hits:
        search_block = "搜索结果摘要：\n" + "\n".join(
            f"- {h.title[:100]} | {h.snippet[:180]}" for h in pool.hits[:20]
        )
    else:
        search_block = "（无搜索结果，请结合公开认知谨慎列举。）"

    messages = [
        {
            "role": "system",
            "content": (
                '你是竞品研究专家。只输出 JSON：{"domains": [], "brand_names": string[]}。'
                "只填 brand_names（最多 5 个）。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"目标品牌：{brand}\n"
                f"行业：{profile.get('industry') or '—'}\n"
                f"市场：{region_label}（{language}）\n\n"
                f"{search_block}\n\n"
                "列出直接竞品品牌名，禁止编造。"
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
