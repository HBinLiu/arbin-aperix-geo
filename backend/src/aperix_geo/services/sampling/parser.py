"""v0 parsing: mentions, URLs, rank, brand-local sentiment (LLM judge)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from aperix_geo.db.models import Competitor, Subject, SubjectType
from aperix_geo.services.analysis._labels import competitor_rank_label, own_label
from aperix_geo.utils.url import (
    extract_urls,
    filter_citation_urls,
    host_matches_root,
    hostname_from_url,
    normalize_domain,
)

if TYPE_CHECKING:
    from aperix_geo.services.crawl.settings import PageCrawlSettings


@dataclass(frozen=True)
class _CompetitorEntry:
    label: str
    brand: str
    terms: tuple[str, ...]
    domain: str


def _collect_match_terms(*parts: str | None) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for term in parts:
        text = (term or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(text)
    return names


def _own_names(subject: Subject) -> list[str]:
    """主体提及匹配词：brand、domain、aliases 均参与（两种 Subject.type 一致）。"""
    return _collect_match_terms(
        subject.brand,
        subject.domain,
        *(str(x) for x in (subject.aliases or []) if x),
    )


def _competitor_entry(competitor: Competitor) -> _CompetitorEntry | None:
    brand = (competitor.brand or "").strip()
    domain = (competitor.domain or "").strip()
    label = competitor_rank_label(brand=brand, domain=domain)
    if not label:
        return None
    terms = _collect_match_terms(brand, domain)
    return _CompetitorEntry(label=label, brand=brand, terms=tuple(terms), domain=domain)


def _competitor_entries(subject: Subject) -> list[_CompetitorEntry]:
    entries: list[_CompetitorEntry] = []
    seen: set[str] = set()
    for competitor in subject.competitors or []:
        entry = _competitor_entry(competitor)
        if not entry:
            continue
        key = entry.label.lower()
        if key in seen:
            continue
        seen.add(key)
        entries.append(entry)
    return entries


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


def _count_terms(text: str, terms: list[str] | tuple[str, ...]) -> int:
    return sum(_count_term(text, term) for term in terms if term)


def _host_mentions_domain(domain: str, url_hosts: list[str]) -> bool:
    if not domain or not url_hosts:
        return False
    root = normalize_domain(domain) or domain.lower()
    label = domain.split(".")[0].lower()
    for host in url_hosts:
        hl = (host or "").lower()
        if label in hl or host_matches_root(host, root):
            return True
    return False


def _first_idx(text: str, term: str) -> int | None:
    if not term:
        return None
    idx = text.lower().find(term.lower())
    return idx if idx >= 0 else None


def _first_idx_any(text: str, terms: list[str] | tuple[str, ...]) -> int | None:
    indices = [_first_idx(text, term) for term in terms if term]
    valid = [idx for idx in indices if idx is not None]
    return min(valid) if valid else None


def _ordered_rank_names(subject: Subject, competitors: list[_CompetitorEntry]) -> list[str]:
    names: list[str] = []
    for n in _own_names(subject):
        if n not in names:
            names.append(n)
    for entry in competitors:
        if entry.label not in names:
            names.append(entry.label)
    return names


def _compute_rank_own(
    raw_text: str,
    *,
    subject: Subject,
    competitors: list[_CompetitorEntry],
) -> int | None:
    """Rank by first occurrence index among all mentioned candidates."""
    candidates: list[tuple[str, int]] = []
    for name in _own_names(subject):
        idx = _first_idx(raw_text, name)
        if idx is not None:
            candidates.append((name, idx))
    for entry in competitors:
        idx = _first_idx_any(raw_text, entry.terms)
        if idx is not None:
            candidates.append((entry.label, idx))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[1])
    own_set = {n.lower() for n in _own_names(subject)}
    for rank, (name, _) in enumerate(candidates, start=1):
        if name.lower() in own_set:
            return rank
    return None


def _parse_competitor_mentions(
    text: str,
    url_hosts: list[str],
    competitors: list[_CompetitorEntry],
) -> tuple[dict[str, bool], dict[str, int]]:
    mentions: dict[str, bool] = {}
    counts: dict[str, int] = {}
    for entry in competitors:
        count = _count_terms(text, entry.terms)
        host_hit = _host_mentions_domain(entry.domain, url_hosts)
        if count == 0 and host_hit:
            count = 1
        mentions[entry.label] = count > 0 or host_hit
        counts[entry.label] = count
    return mentions, counts


def _citation_root(subject: Subject) -> str | None:
    if subject.website_url:
        root = normalize_domain(hostname_from_url(subject.website_url))
        if root:
            return root
    if subject.type == SubjectType.domain and subject.domain:
        return normalize_domain(subject.domain)
    return None


def _url_matches_competitor(url: str, entry: _CompetitorEntry) -> bool:
    if not entry.domain:
        return False
    root = normalize_domain(entry.domain) or entry.domain.lower()
    return host_matches_root(hostname_from_url(url), root)


def _url_target(url: str, *, root: str | None, competitors: list[_CompetitorEntry]) -> str:
    if root and host_matches_root(hostname_from_url(url), root):
        return "own"
    for entry in competitors:
        if _url_matches_competitor(url, entry):
            return entry.label
    return ""


def _resolve_citation_sources(
    urls: list[str],
    *,
    root: str | None,
    own_names: list[str],
    own_brand: str,
    competitors: list[_CompetitorEntry],
    crawl: PageCrawlSettings,
    snippet_chars: int,
    llm_enabled: bool,
    geo_cache_ttl_s: int,
    geo_batch_size: int,
) -> dict[str, Any]:
    """并行抓取来源页；批量 Page GEO / 来源页提及分析。"""
    from aperix_geo.services.sampling.citation_analysis import (
        analyze_citation_pages_geo,
        brand_names_match,
        heuristic_page_mentioned_brands,
        page_mentioned_brand_names,
    )
    from aperix_geo.services.sampling.citation_page import fetch_citation_pages_parallel

    competitor_brand_names = [entry.brand or entry.label for entry in competitors if entry.brand or entry.label]
    own_brand_keys = _collect_match_terms(own_brand, *own_names)

    citation_urls_own = [u for u in urls if root and host_matches_root(hostname_from_url(u), root)]
    has_own_domain_link = len(citation_urls_own) > 0

    has_competitor_domain_links: dict[str, bool] = {entry.label: False for entry in competitors}
    cited_competitors_on_source: dict[str, bool] = {entry.label: False for entry in competitors}

    for url in urls:
        for entry in competitors:
            if _url_matches_competitor(url, entry):
                has_competitor_domain_links[entry.label] = True

    citation_sources: list[dict[str, Any]] = []
    cited_own_domain = False

    pages = fetch_citation_pages_parallel(
        urls,
        crawl=crawl,
        snippet_chars=snippet_chars,
    )

    if llm_enabled:
        page_analyses = analyze_citation_pages_geo(
            pages,
            own_brand=own_brand,
            competitors=competitor_brand_names,
            cache_ttl_s=geo_cache_ttl_s,
            batch_size=geo_batch_size,
        )
    else:
        page_analyses = []
        for page in pages:
            if page.fetch_ok:
                page_analyses.append(
                    {
                        "page_mentioned_brands": heuristic_page_mentioned_brands(
                            page,
                            own_brand=own_brand,
                            competitors=competitor_brand_names,
                            own_aliases=own_names,
                        ),
                        "domain_classification": {"type": "", "reason": ""},
                        "url_classification": {"type": "", "reason": ""},
                        "analysis_source": "heuristic",
                    },
                )
            else:
                page_analyses.append({})

    for page, page_analysis in zip(pages, page_analyses):
        target = _url_target(page.url, root=root, competitors=competitors)
        page_mentioned = page_mentioned_brand_names(page_analysis)

        if target == "own" and brand_names_match(own_brand_keys, page_mentioned):
            cited_own_domain = True
        for entry in competitors:
            entry_keys = _collect_match_terms(entry.brand, entry.label)
            if brand_names_match(entry_keys, page_mentioned):
                cited_competitors_on_source[entry.label] = True

        domain_cls = (
            page_analysis.get("domain_classification")
            if isinstance(page_analysis.get("domain_classification"), dict)
            else {}
        )
        url_cls = (
            page_analysis.get("url_classification")
            if isinstance(page_analysis.get("url_classification"), dict)
            else {}
        )

        citation_sources.append(
            {
                "url": page.url,
                "domain": page.domain,
                "http_status": page.http_status,
                "page_title": page.title,
                "description": page.description,
                "headings": page.headings,
                "has_table": page.has_table,
                "has_code_block": page.has_code_block,
                "text_snippet": page.text_snippet,
                "fetch_ok": page.fetch_ok,
                "target": target,
                "domain_type": str(domain_cls.get("type") or domain_cls.get("detected_domain_type") or "").strip(),
                "url_type": str(url_cls.get("type") or url_cls.get("detected_type") or "").strip(),
                "llm_analysis": page_analysis,
            }
        )

    return {
        "citation_urls_own": citation_urls_own,
        "has_own_domain_link": has_own_domain_link,
        "cited_own_domain": cited_own_domain,
        "citation_sources": citation_sources,
        "has_competitor_domain_links": has_competitor_domain_links,
        "cited_competitors_on_source": cited_competitors_on_source,
    }


def _empty_citation_result() -> dict[str, Any]:
    return {
        "citation_urls_own": [],
        "has_own_domain_link": False,
        "cited_own_domain": False,
        "citation_sources": [],
        "has_competitor_domain_links": {},
        "cited_competitors_on_source": {},
    }


def _parsed_sentiment_from_absa(
    response_absa: dict[str, Any],
    *,
    own_brand: str,
    competitor_absa_keys: list[tuple[str, str]],
    mentions_own: bool,
    mentions_competitors: dict[str, bool],
) -> dict[str, Any]:
    from aperix_geo.services.sampling.sentiment import parsed_sentiment_from_absa

    return parsed_sentiment_from_absa(
        response_absa,
        own_brand=own_brand,
        competitor_keys=competitor_absa_keys,
        mentions_own=mentions_own,
        mentions_competitors=mentions_competitors,
    )


def parse_llm_output(
    raw_text: str,
    *,
    subject: Subject,
    source_urls: list[str] | None = None,
    web_search_mode: str = "none",
) -> dict[str, Any]:
    text = raw_text or ""
    urls = filter_citation_urls(extract_urls(text))
    if source_urls:
        urls = filter_citation_urls(list(dict.fromkeys([*urls, *[u for u in source_urls if u]])))
    url_hosts: list[str] = []
    for u in urls:
        h = hostname_from_url(u)
        if h:
            url_hosts.append(h)

    own_names = _own_names(subject)
    mention_count_own = sum(_count_term(text, n) for n in own_names if n)
    mentions_own = mention_count_own > 0

    competitors = _competitor_entries(subject)
    mentions_competitors, mention_counts_competitors = _parse_competitor_mentions(
        text, url_hosts, competitors
    )

    own_lab = own_label(subject)
    rank_hints: dict[str, int | None] = {own_lab: _first_idx_any(text, own_names)}
    for entry in competitors:
        rank_hints[entry.label] = _first_idx_any(text, entry.terms)

    rank_own = _compute_rank_own(text, subject=subject, competitors=competitors)

    root = _citation_root(subject)
    from aperix_geo.config import get_settings

    settings = get_settings()
    from aperix_geo.services.crawl.settings import PageCrawlSettings, page_crawl_settings

    crawl = page_crawl_settings(settings)
    own_brand = subject.brand or own_lab

    competitor_absa_keys: list[tuple[str, str]] = []
    competitor_brand_names: list[str] = []
    seen_absa_keys: set[str] = set()
    for entry in competitors:
        absa_key = entry.brand or entry.label
        if absa_key not in seen_absa_keys:
            seen_absa_keys.add(absa_key)
            competitor_brand_names.append(absa_key)
        competitor_absa_keys.append((absa_key, entry.label))

    absa_needed = (
        (mentions_own or any(mentions_competitors.values()))
        and bool(settings.deepseek_api_key.strip())
    )
    citation_kwargs = dict(
        urls=urls,
        root=root,
        own_names=own_names,
        own_brand=own_brand,
        competitors=competitors,
        crawl=crawl,
        snippet_chars=settings.citation_text_snippet_chars,
        llm_enabled=settings.citation_page_geo_llm_enabled and bool(settings.deepseek_api_key.strip()),
        geo_cache_ttl_s=settings.citation_page_geo_cache_ttl_s,
        geo_batch_size=settings.citation_page_geo_batch_size,
    )

    response_absa: dict[str, Any] = {}
    citation = _empty_citation_result()

    if absa_needed and urls:
        from concurrent.futures import ThreadPoolExecutor

        from aperix_geo.services.sampling.citation_analysis import analyze_citation_response_absa

        def _run_absa() -> dict[str, Any]:
            return analyze_citation_response_absa(
                text,
                own_brand=own_brand,
                competitors=competitor_brand_names,
                cache_ttl_s=settings.citation_response_absa_cache_ttl_s,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            citation_future = pool.submit(_resolve_citation_sources, **citation_kwargs)
            absa_future = pool.submit(_run_absa)
            citation = citation_future.result()
            response_absa = absa_future.result()
    elif absa_needed:
        from aperix_geo.services.sampling.citation_analysis import analyze_citation_response_absa

        response_absa = analyze_citation_response_absa(
            text,
            own_brand=own_brand,
            competitors=competitor_brand_names,
            cache_ttl_s=settings.citation_response_absa_cache_ttl_s,
        )
    elif urls:
        citation = _resolve_citation_sources(**citation_kwargs)

    sentiment_own = "neutral"
    sentiment_score_own: float | None = None
    sentiment_reason_own: str | None = None
    sentiment_competitors: dict[str, str] = {}
    sentiment_scores_competitors: dict[str, float] = {}
    sentiment_reasons_competitors: dict[str, str] = {}
    sentiment_source = "none"

    if response_absa:
        llm_sentiment = _parsed_sentiment_from_absa(
            response_absa,
            own_brand=own_brand,
            competitor_absa_keys=competitor_absa_keys,
            mentions_own=mentions_own,
            mentions_competitors=mentions_competitors,
        )
        sentiment_own = llm_sentiment["sentiment_own"]
        sentiment_score_own = llm_sentiment["sentiment_score_own"]
        sentiment_reason_own = llm_sentiment["sentiment_reason_own"]
        sentiment_competitors = llm_sentiment["sentiment_competitors"]
        sentiment_scores_competitors = llm_sentiment["sentiment_scores_competitors"]
        sentiment_reasons_competitors = llm_sentiment["sentiment_reasons_competitors"]
        sentiment_source = llm_sentiment["sentiment_source"]

    return {
        "urls": urls,
        "url_hosts": url_hosts,
        "mentions_own": mentions_own,
        "mention_count_own": mention_count_own,
        "mentions_competitors": mentions_competitors,
        "mention_counts_competitors": mention_counts_competitors,
        "sentiment_own": sentiment_own,
        "sentiment_score_own": sentiment_score_own,
        "sentiment_reason_own": sentiment_reason_own,
        "sentiment_competitors": sentiment_competitors,
        "sentiment_scores_competitors": sentiment_scores_competitors,
        "sentiment_reasons_competitors": sentiment_reasons_competitors,
        "sentiment_source": sentiment_source,
        "web_search_mode": web_search_mode,
        "source_urls_from_api": list(source_urls or []),
        "rank_hints_first_index": rank_hints,
        "rank_own": rank_own,
        "citation_response_absa": response_absa,
        **citation,
    }
