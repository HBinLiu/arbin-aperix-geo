"""竞品发现可调参数（.env 中 COMPETITOR_*，经 Settings 读取）。"""

from __future__ import annotations

from aperix_geo.config import get_settings

# 旧常量名 → Settings 字段（便于模块内 from defaults import RESULT_MAX 等）
_ATTR_MAP: dict[str, str] = {
    "METADATA_TIMEOUT_S": "competitor_site_fetch_timeout_s",
    "METADATA_CONCURRENCY": "competitor_site_fetch_concurrency",
    "HOMEPAGE_TIMEOUT_S": "competitor_target_fetch_timeout_s",
    "CROSS_VALIDATE_BATCH_SIZE": "competitor_cross_validate_batch_size",
    "SEARCH_PAGE_SIZE": "competitor_search_page_size",
    "RESULT_MIN": "competitor_result_min",
    "RESULT_MAX": "competitor_result_max",
}


def __getattr__(name: str):
    field = _ATTR_MAP.get(name)
    if field is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(get_settings(), field)


def __dir__() -> list[str]:
    return sorted(_ATTR_MAP.keys())
