"""Phase 3 — merge: ABSA + citation into entity signal drafts."""

from __future__ import annotations

from typing import Any

from aperix_geo.services.sampling.citation.apply import apply_citation_to_drafts
from aperix_geo.services.sampling.citation import CitationDocument
from aperix_geo.services.sampling.mentions import own_names
from aperix_geo.services.sampling.parse.context import ParseContext
from aperix_geo.services.sampling.parse.types import ParseEnrichment, ParseMergeResult
from aperix_geo.services.sampling.sentiment import (
    apply_response_absa_to_drafts,
    reset_sentiment_drafts,
)
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft, normalize_draft_metrics


def merge_parse_results(
    ctx: ParseContext,
    *,
    enrichment: ParseEnrichment,
) -> ParseMergeResult:
    drafts = ctx.entity_signals
    response_absa = enrichment.response_absa
    if response_absa:
        sentiment_source, response_absa = apply_response_absa_to_drafts(
            drafts,
            response_absa,
            subject=ctx.subject,
            db=ctx.db,
            own_brand=ctx.own_brand,
            competitor_brand_names=ctx.competitor_brand_names,
            competitor_absa_keys=ctx.competitor_absa_keys,
            url_hosts=ctx.url_hosts,
            competitors=ctx.competitors,
            text=ctx.text,
            excluded_keys=set(ctx.configured_brand_keys),
        )
    else:
        reset_sentiment_drafts(drafts)
        sentiment_source = "none"

    apply_citation_to_drafts(
        drafts,
        enrichment.citation,
        own_brand=ctx.own_brand,
        own_names=own_names(ctx.subject),
        competitors=ctx.competitors,
    )
    for draft in drafts:
        normalize_draft_metrics(draft)
    return ParseMergeResult(
        entity_signals=drafts,
        sentiment_source=sentiment_source,
        response_absa=response_absa,
    )


def finalize_entity_signals(
    ctx: ParseContext,
    *,
    citation: CitationDocument,
    response_absa: dict[str, Any],
) -> tuple[list[EntitySignalDraft], str, dict[str, Any]]:
    """Legacy API: returns (drafts, sentiment_source, response_absa)."""
    merged = merge_parse_results(
        ctx,
        enrichment=ParseEnrichment(citation=citation, response_absa=response_absa),
    )
    return merged.entity_signals, merged.sentiment_source, merged.response_absa
