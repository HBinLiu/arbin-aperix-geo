"""Setup 向导 Redis 缓存（会话、画像、提示词）。

UI 顺序：设置 → 选竞品 → 审主题 → 确认提示词。
API：`POST /subjects/setup/discover` → `.../topics` → `.../prompts` → `.../finalize`。
"""

from aperix_geo.services.setup.cache.discover import (
    find_active_discover_session,
    get_discover_job,
    set_discover_job,
    wait_discover_job,
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

__all__ = [
    "cached_prompts",
    "create_session",
    "delete_session",
    "find_active_discover_session",
    "get_discover_job",
    "get_profile_cache",
    "get_session",
    "profile_hash",
    "prompts_generation_hash",
    "set_discover_job",
    "set_profile_cache",
    "update_session",
    "wait_discover_job",
]
