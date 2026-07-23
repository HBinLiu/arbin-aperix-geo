"""Shallalist-aligned domain content type codes.

English codes are stored in DB; Chinese labels live on the frontend
(``DOMAIN_TYPE_LABELS``). Classification uses curated seeds + light heuristics.
"""

from __future__ import annotations

DOMAIN_TYPES: frozenset[str] = frozenset(
    {
        "adv",
        "alcohol",
        "automobile",
        "dating",
        "downloads",
        "drugs",
        "education",
        "finance",
        "fortunetelling",
        "forum",
        "gamble",
        "government",
        "hobby",
        "hospitals",
        "imagehosting",
        "isp",
        "jobsearch",
        "models",
        "movies",
        "music",
        "news",
        "politics",
        "porn",
        "radiotv",
        "recreation",
        "redirector",
        "religion",
        "science",
        "searchengines",
        "sex",
        "shopping",
        "socialnet",
        "spyware",
        "tracker",
        "urlshortener",
        "warez",
        "weapons",
        "webmail",
        "webradio",
        "other",
    }
)

DEFAULT_DOMAIN_TYPE = "other"


def normalize_domain_type(value: str | None) -> str:
    key = (value or "").strip().lower()
    if not key:
        return DEFAULT_DOMAIN_TYPE
    return key if key in DOMAIN_TYPES else DEFAULT_DOMAIN_TYPE
