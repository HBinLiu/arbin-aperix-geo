"""v0 parsing: mentions, URLs, crude sentiment, rank, brand-local sentiment."""

from __future__ import annotations

import re
from typing import Any

from aperix_geo.db.models import Subject, SubjectType
from aperix_geo.utils.url import (
    extract_urls,
    host_matches_root,
    hostname_from_url,
    normalize_domain,
)

_SENTENCE_SPLIT_RE = re.compile(r"[。！？\n]+|[.!?]+\s+")

# Very naive sentiment lexicon for Chinese + a few English markers
_POS = ("好", "优秀", "推荐", "领先", "正面", "值得信赖", "不错", "满意", "good", "great", "excellent")
_NEG = ("差", "糟糕", "风险", "负面", "问题", "不推荐", "避免", "投诉", "bad", "poor", "avoid", "scam")

_SENTIMENT_SCORE = {"positive": 1.0, "neutral": 0.5, "negative": 0.0}


def _own_names(subject: Subject) -> list[str]:
    names: list[str] = []
    if subject.type == SubjectType.brand and subject.brand:
        names.append(subject.brand)
    if subject.aliases:
        names.extend(str(x) for x in subject.aliases if x)
    if subject.type == SubjectType.domain and subject.domain:
        names.append(subject.domain)
    return names


def _count_term(text: str, term: str) -> int:
    if not term or not text:
        return 0
    t = text.lower()
    needle = term.lower()
    count = start = 0
    while True:
        idx = t.find(needle, start)
        if idx < 0:
            break
        count += 1
        start = idx + len(needle)
    return count


def _mentions_term(text: str, term: str) -> bool:
    return _count_term(text, term) > 0


def _crude_sentiment(text: str) -> str:
    t = text or ""
    pos = sum(1 for w in _POS if w.lower() in t.lower())
    neg = sum(1 for w in _NEG if w.lower() in t.lower())
    if neg > pos:
        return "negative"
    if pos > neg:
        return "positive"
    return "neutral"


def _sentiment_score(label: str) -> float:
    return _SENTIMENT_SCORE.get(label, 0.5)


def _sentences_with_terms(text: str, terms: list[str]) -> str:
    if not text or not terms:
        return ""
    parts: list[str] = []
    for chunk in _SENTENCE_SPLIT_RE.split(text):
        chunk = chunk.strip()
        if not chunk:
            continue
        if any(_mentions_term(chunk, t) for t in terms if t):
            parts.append(chunk)
    return " ".join(parts)


def _ordered_brand_names(subject: Subject, competitor_brands: list[str]) -> list[str]:
    """Canonical order for rank guess: own brand first, then competitors."""
    names: list[str] = []
    for n in _own_names(subject):
        if n not in names:
            names.append(n)
    for c in competitor_brands:
        if c not in names:
            names.append(c)
    return names


def _first_idx(text: str, term: str) -> int | None:
    if not term:
        return None
    idx = text.lower().find(term.lower())
    return idx if idx >= 0 else None


def _compute_rank_own(
    raw_text: str,
    *,
    subject: Subject,
    competitor_brands: list[str],
    competitor_domains: list[str],
) -> int | None:
    """Rank by first occurrence index among all mentioned candidates."""
    candidates: list[tuple[str, int]] = []
    for name in _own_names(subject):
        idx = _first_idx(raw_text, name)
        if idx is not None:
            candidates.append((name, idx))
    for c in competitor_brands:
        idx = _first_idx(raw_text, c)
        if idx is not None:
            candidates.append((c, idx))
    for d in competitor_domains:
        idx = _first_idx(raw_text, d)
        if idx is not None:
            candidates.append((d, idx))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1])
    own_set = {n.lower() for n in _own_names(subject)}
    for rank, (name, _) in enumerate(candidates, start=1):
        if name.lower() in own_set:
            return rank
    return None


def _citation_root(subject: Subject) -> str | None:
    if subject.website_url:
        root = normalize_domain(hostname_from_url(subject.website_url))
        if root:
            return root
    if subject.type == SubjectType.domain and subject.domain:
        return normalize_domain(subject.domain)
    return None


def parse_llm_output(
    raw_text: str,
    *,
    subject: Subject,
    competitor_domains: list[str],
    competitor_brands: list[str],
) -> dict[str, Any]:
    text = raw_text or ""
    urls = extract_urls(text)
    url_hosts: list[str] = []
    for u in urls:
        h = hostname_from_url(u)
        if h:
            url_hosts.append(h)

    own_names = _own_names(subject)
    mention_count_own = sum(_count_term(text, n) for n in own_names if n)
    mentions_own = mention_count_own > 0

    mention_counts_competitors: dict[str, int] = {}
    mentions_competitors: dict[str, bool] = {}
    for c in competitor_brands:
        cnt = _count_term(text, c)
        mention_counts_competitors[c] = cnt
        mentions_competitors[c] = cnt > 0
    for d in competitor_domains:
        cnt = _count_term(text, d)
        mention_counts_competitors[d] = cnt
        mentions_competitors[d] = cnt > 0 or any(
            d.split(".")[0].lower() in (h or "").lower() for h in url_hosts
        )

    rank_hints: dict[str, int | None] = {}
    for name in _ordered_brand_names(subject, competitor_brands):
        rank_hints[name] = _first_idx(text, name)

    rank_own = _compute_rank_own(
        text,
        subject=subject,
        competitor_brands=competitor_brands,
        competitor_domains=competitor_domains,
    )

    root = _citation_root(subject)
    citation_urls_own = [u for u in urls if host_matches_root(hostname_from_url(u), root)]
    cited_own_domain = len(citation_urls_own) > 0

    brand_snippet = _sentences_with_terms(text, own_names)
    sentiment_own = _crude_sentiment(brand_snippet) if mentions_own else "neutral"
    sentiment_score_own = _sentiment_score(sentiment_own) if mentions_own else None

    return {
        "urls": urls,
        "url_hosts": url_hosts,
        "mentions_own": mentions_own,
        "mention_count_own": mention_count_own,
        "mentions_competitors": mentions_competitors,
        "mention_counts_competitors": mention_counts_competitors,
        "sentiment_crude": _crude_sentiment(text),
        "sentiment_own": sentiment_own,
        "sentiment_score_own": sentiment_score_own,
        "rank_hints_first_index": rank_hints,
        "rank_own": rank_own,
        "cited_own_domain": cited_own_domain,
        "citation_urls_own": citation_urls_own,
    }
