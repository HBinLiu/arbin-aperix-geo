"""Citation page crawl for the sampling crawl phase."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from aperix_geo.db.models import LLMResponse, Subject
from aperix_geo.services.sampling.parse.analysis import crawl_citation_pages
from aperix_geo.services.sampling.parse.context import extract_parse_context
from aperix_geo.services.sampling.workflow.execute import chat_result_from_row


def crawl_response_citations(
    *,
    row: LLMResponse,
    subject: Subject,
    db: Session | None = None,
) -> None:
    """Fetch citation source pages for a response (IO-bound; runs on crawl workers)."""
    chat_result = chat_result_from_row(row)
    ctx = extract_parse_context(
        row.raw_text or "",
        subject=subject,
        source_urls=list(chat_result.source_urls),
        web_search_mode=chat_result.web_search_mode,
        sampling_job_id=row.sampling_job_id,
        db=db,
    )
    if not ctx.urls:
        return
    crawl_citation_pages(ctx.citation)
