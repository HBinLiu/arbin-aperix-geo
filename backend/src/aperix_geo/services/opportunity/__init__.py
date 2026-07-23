"""Opportunity domain services."""

from aperix_geo.services.opportunity.prompt_fanouts import (
    build_prompt_fanouts_page,
    dismiss_opportunity_prompt_fanout,
    promote_opportunity_prompt_fanout,
)

__all__ = [
    "build_prompt_fanouts_page",
    "dismiss_opportunity_prompt_fanout",
    "promote_opportunity_prompt_fanout",
]
