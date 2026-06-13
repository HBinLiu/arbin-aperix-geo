"""竞品发现可调参数（读取 Settings）。"""

from __future__ import annotations

from aperix_geo.config import get_settings

_SETTINGS_FIELDS: dict[str, str] = {
    "CROSS_VALIDATE_BATCH_SIZE": "competitor_cross_validate_batch_size",
    "POOL_SIZE": "competitor_pool_size",
    "SEARCH_PAGE_SIZE": "competitor_search_page_size",
    "SEARCH_ROUNDS": "competitor_search_rounds",
    "RESULT_MIN": "competitor_result_min",
    "RESULT_MAX": "competitor_result_max",
}


def __getattr__(name: str):
    field = _SETTINGS_FIELDS.get(name)
    if field is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(get_settings(), field)


def __dir__() -> list[str]:
    return sorted(_SETTINGS_FIELDS.keys())
