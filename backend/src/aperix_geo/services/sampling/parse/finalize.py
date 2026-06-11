"""Merge ABSA and citation results into entity signal drafts."""

from __future__ import annotations

from typing import Any

from aperix_geo.services.sampling.citation.apply import apply_citation_to_drafts
from aperix_geo.services.sampling.citation import CitationDocument
from aperix_geo.services.sampling.mentions import own_names
from aperix_geo.services.sampling.parse.context import ParseContext
from aperix_geo.services.sampling.sentiment import (
    apply_response_absa_to_drafts,
    reset_sentiment_drafts,
)
from aperix_geo.services.sampling.signal_draft import EntitySignalDraft, normalize_draft_metrics


def finalize_entity_signals(
    ctx: ParseContext,
    *,
    citation: CitationDocument,
    response_absa: dict[str, Any],
) -> tuple[list[EntitySignalDraft], str]:
    drafts = ctx.entity_signals
    if response_absa:
        sentiment_source = apply_response_absa_to_drafts(
            drafts,
            response_absa,
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
        citation,
        own_brand=ctx.own_brand,
        own_names=own_names(ctx.subject),
        competitors=ctx.competitors,
    )
    for draft in drafts:
        normalize_draft_metrics(draft)
    return drafts, sentiment_source
