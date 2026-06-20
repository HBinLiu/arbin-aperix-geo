"""Apply document-layer citation results onto entity signal drafts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aperix_geo.services.sampling.citation.document import CitationDocument
from aperix_geo.services.sampling.citation.labels import brand_names_match, page_mentioned_brand_names
from aperix_geo.services.sampling.mentions import CompetitorEntry, collect_match_terms

if TYPE_CHECKING:
    from aperix_geo.services.sampling.signal_draft import EntitySignalDraft


def reset_citation_drafts(drafts: list[EntitySignalDraft]) -> None:
    for draft in drafts:
        draft.has_domain_link = False
        draft.cited_on_source = False


def apply_citation_to_drafts(
    drafts: list[EntitySignalDraft],
    citation: CitationDocument,
    *,
    own_brand: str,
    own_names: list[str],
    competitors: list[CompetitorEntry],
) -> None:
    """Derive per-entity has_domain_link / cited_on_source from citation document fields."""
    if not citation.citation_urls_own and not citation.citation_sources:
        reset_citation_drafts(drafts)
        return

    by_entity_label = {draft.entity_label: draft for draft in drafts}
    own_draft = next(draft for draft in drafts if draft.entity_kind == "own")
    own_brand_keys = collect_match_terms(own_brand, *own_names)

    own_draft.has_domain_link = bool(citation.citation_urls_own)
    own_draft.cited_on_source = False
    for draft in drafts:
        if draft.entity_kind in ("competitor", "other"):
            if draft.entity_kind == "competitor":
                draft.has_domain_link = False
            draft.cited_on_source = False

    for source in citation.citation_sources:
        target = str(source.get("target") or "")
        if target and target != "own":
            draft = by_entity_label.get(target)
            if draft is not None:
                draft.has_domain_link = True

    for source in citation.citation_sources:
        page_analysis = source.get("llm_analysis")
        if not isinstance(page_analysis, dict):
            page_analysis = {}
        page_mentioned = page_mentioned_brand_names(page_analysis)
        target = str(source.get("target") or "")

        if target == "own" and brand_names_match(own_brand_keys, page_mentioned):
            own_draft.cited_on_source = True

        for entry in competitors:
            draft = by_entity_label.get(entry.label)
            if draft is None:
                continue
            entry_keys = list(entry.terms) or collect_match_terms(entry.brand, entry.label)
            if brand_names_match(entry_keys, page_mentioned):
                draft.cited_on_source = True

        for draft in drafts:
            if draft.entity_kind != "other":
                continue
            keys = collect_match_terms(draft.entity_label)
            if brand_names_match(keys, page_mentioned):
                draft.cited_on_source = True
