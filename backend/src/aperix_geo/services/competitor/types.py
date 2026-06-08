"""Shared types for competitor discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

from aperix_geo.services.web_search import SearchHit


class NicheProfile(TypedDict):
    company: str
    industry: str
    core_features: str
    target_customers: str
    micro_keywords: str


class DiscoveredCompetitor(TypedDict):
    domain: str
    website_url: str
    brand: str
    summary: str


@dataclass(frozen=True)
class CompetitorScore:
    domain: str
    score: float
    reason: str


@dataclass(frozen=True)
class SiteHead:
    domain: str
    title: str
    description: str
    reachable: bool


@dataclass
class SearchPool:
    """SearXNG 去重后的主域名候选及原始命中。"""

    domains: list[str]
    hits: list[SearchHit]
    hit_by_domain: dict[str, SearchHit] = field(default_factory=dict)


@dataclass
class CrossValidateResult:
    scores: list[CompetitorScore]
    heads: dict[str, SiteHead]
