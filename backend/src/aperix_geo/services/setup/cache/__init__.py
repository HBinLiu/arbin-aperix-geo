"""Setup 向导 Redis 缓存（会话、Step1 画像、Step2 竞品、Step3 提示词）。"""

from aperix_geo.services.setup.cache.competitors import (
    cached_competitors_result,
    competitors_search_fingerprint,
    session_patch_after_competitors,
)
from aperix_geo.services.setup.cache.profile import (
    get_profile_cache,
    profile_fingerprint,
    set_profile_cache,
)
from aperix_geo.services.setup.cache.prompts import generate_setup_prompts_for_session
from aperix_geo.services.setup.cache.session import (
    create_session,
    delete_session,
    get_session,
    update_session,
)

__all__ = [
    "cached_competitors_result",
    "competitors_search_fingerprint",
    "create_session",
    "delete_session",
    "generate_setup_prompts_for_session",
    "get_profile_cache",
    "get_session",
    "profile_fingerprint",
    "session_patch_after_competitors",
    "set_profile_cache",
    "update_session",
]
