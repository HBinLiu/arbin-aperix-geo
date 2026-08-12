"""竞品相关服务（手填竞品、画像、别名 enrich 等）。"""

from aperix_geo.services.competitor.profile import normalize_niche_profile
from aperix_geo.services.competitor.summary import fallback_profile_summary

__all__ = [
    "fallback_profile_summary",
    "normalize_niche_profile",
]
