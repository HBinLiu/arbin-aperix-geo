"""Setup 向导 Redis 缓存（会话、画像、竞品、提示词）。

UI 顺序：设置 → 选竞品 → 审主题 → 确认提示词。
API：`POST /subjects/setup/discover` → `.../topics` → `.../prompts` → `.../finalize`。
"""

from aperix_geo.services.setup.cache.competitors import (
    cached_competitors_result,
    competitors_search_hash,
    session_patch_after_competitors,
)
from aperix_geo.services.setup.cache.profile import (
    get_profile_cache,
    profile_hash,
    set_profile_cache,
)
from aperix_geo.services.setup.cache.prompts import cached_prompts, prompts_generation_hash
from aperix_geo.services.setup.cache.session import (
    create_session,
    delete_session,
    get_session,
    update_session,
)
from aperix_geo.services.setup.prompts import generate_setup_prompts_for_session

__all__ = [
    "cached_competitors_result",
    "cached_prompts",
    "competitors_search_hash",
    "create_session",
    "delete_session",
    "generate_setup_prompts_for_session",
    "get_profile_cache",
    "get_session",
    "profile_hash",
    "prompts_generation_hash",
    "session_patch_after_competitors",
    "set_profile_cache",
    "update_session",
]
