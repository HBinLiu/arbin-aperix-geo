"""Shared types for competitor discovery."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, NotRequired, TypedDict

SubjectType = Literal["domain", "brand"]


class NicheProfile(TypedDict):
    company: str
    industry: str
    features: str
    customers: str
    search_queries: str
    category_terms: str
    scenario_terms: str
    audience_terms: str
    pain_terms: str


class DiscoveredCompetitor(TypedDict):
    domain: str
    website_url: str
    brand: str
    summary: NotRequired[str]
    aliases: NotRequired[list[str]]


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
    seo: str = ""
    resolved_url: str = ""
    brand_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateMeta:
    domain: str
    brand: str
    website_url: str


@dataclass
class CandidatePool:
    """交叉验算候选池。"""

    domains: list[str]
    by_domain: dict[str, CandidateMeta] = field(default_factory=dict)


@dataclass
class CrossValidateResult:
    scores: list[CompetitorScore]
    heads: dict[str, SiteHead]
