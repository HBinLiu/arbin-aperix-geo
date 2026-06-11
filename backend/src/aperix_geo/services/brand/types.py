"""Brand sync input types (decoupled from sampling drafts)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrandSyncEntity:
    """Minimal entity descriptor for brand registry upsert."""

    entity_id: str
    entity_kind: str
    entity_label: str
    brand: str = ""
    domain: str = ""
    website_url: str = ""
    aliases: tuple[str, ...] = ()
    summary: str = ""
