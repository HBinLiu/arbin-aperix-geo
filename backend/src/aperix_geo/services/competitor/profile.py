"""微观利基画像：精简字段 company / industry / keywords / brief。"""

from __future__ import annotations

import re
from typing import Any

from aperix_geo.services.competitor.types import NicheProfile

MAX_KEYWORDS = 5

REGION_LABELS = {"CN": "中国大陆", "HK": "中国香港", "TW": "中国台湾"}
LANGUAGE_LABELS = {
    "zh-CN": "简体中文",
    "zh-HK": "繁体中文（香港）",
    "zh-TW": "繁体中文（台湾）",
}


def region_label(region: str) -> str:
    return REGION_LABELS.get(region, region)


def language_label(language: str) -> str:
    return LANGUAGE_LABELS.get(language, language)


def _split_tags(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [p.strip() for p in re.split(r"[、,，;；\n|/]", raw) if p.strip()]


def _join_tags(items: list[str], *, limit: int) -> str:
    return "、".join(items[:limit])


def _normalize_term_list(raw: Any, *, limit: int) -> list[str]:
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()][:limit]
    return _split_tags(str(raw or ""))[:limit]


def normalize_niche_profile(data: dict[str, Any], *, entity: str) -> NicheProfile:
    industry = str(data.get("industry") or "未知行业").strip()[:200]
    keywords = _join_tags(_normalize_term_list(data.get("keywords"), limit=MAX_KEYWORDS), limit=MAX_KEYWORDS)
    return NicheProfile(
        company=str(data.get("company") or entity).strip()[:200],
        industry=industry,
        keywords=keywords,
        brief=str(data.get("brief") or "").strip()[:400],
    )


def keywords_list(profile: NicheProfile | dict[str, Any]) -> list[str]:
    return _split_tags(str(profile.get("keywords") or ""))


def profile_to_dict(profile: NicheProfile) -> dict[str, str]:
    return {
        "company": profile.get("company", ""),
        "industry": profile.get("industry", ""),
        "keywords": profile.get("keywords", ""),
        "brief": profile.get("brief", ""),
    }


def profile_from_dict(data: dict[str, Any]) -> NicheProfile:
    return normalize_niche_profile(data if isinstance(data, dict) else {}, entity="")


def merge_profile_updates(
    base: NicheProfile,
    *,
    profile_patch: dict[str, Any] | None = None,
) -> NicheProfile:
    return profile_from_dict({**profile_to_dict(base), **(profile_patch or {})})
