"""Shared types for competitor / niche profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, NotRequired, TypedDict

SubjectType = Literal["domain", "brand"]


class NicheProfile(TypedDict):
    """精简微观利基画像（Setup discover）。"""

    company: str
    industry: str
    keywords: str
    brief: str


class DiscoveredCompetitor(TypedDict):
    domain: str
    website_url: str
    brand: str
    summary: NotRequired[str]
    aliases: NotRequired[list[str]]


@dataclass(frozen=True)
class SiteHead:
    domain: str
    title: str
    description: str
    reachable: bool
    seo: str = ""
    resolved_url: str = ""
    brand_names: tuple[str, ...] = ()
