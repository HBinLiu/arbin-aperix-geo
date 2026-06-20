"""In-memory subject brand index for alias-aware lookup and batch sync."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import Brand
from aperix_geo.utils.domains import registrable_domain


def _normalize_brand_key(name: str) -> str:
    return (name or "").strip().casefold()


def _normalize_domain(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    return registrable_domain(text) or text


@dataclass
class BrandCatalog:
    """Subject-scoped brand rows indexed by normalized name/alias and domain."""

    by_key: dict[str, Brand] = field(default_factory=dict)
    by_domain: dict[str, Brand] = field(default_factory=dict)

    @classmethod
    def load(cls, db: Session, *, subject_id: UUID) -> BrandCatalog:
        catalog = cls()
        rows = db.execute(select(Brand).where(Brand.subject_id == subject_id)).scalars().all()
        for row in rows:
            catalog.register(row)
        return catalog

    def register(self, row: Brand) -> None:
        key = _normalize_brand_key(row.brand)
        if key:
            self.by_key.setdefault(key, row)
        for alias in row.aliases or []:
            alias_key = _normalize_brand_key(str(alias))
            if alias_key:
                self.by_key.setdefault(alias_key, row)
        domain = _normalize_domain(row.domain)
        if domain:
            self.by_domain.setdefault(domain, row)

    def find_by_name_or_alias(self, name: str) -> Brand | None:
        return self.by_key.get(_normalize_brand_key(name))

    def find_by_domain(self, domain: str) -> Brand | None:
        normalized = _normalize_domain(domain)
        if not normalized:
            return None
        return self.by_domain.get(normalized)


@dataclass
class BrandSyncContext:
    """Batch-scoped memo for brand sync within one LLM response."""

    catalog: BrandCatalog
    domain_memo: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, db: Session, *, subject_id: UUID) -> BrandSyncContext:
        return cls(catalog=BrandCatalog.load(db, subject_id=subject_id))

    def memoized_domain(self, brand: str) -> str | None:
        return self.domain_memo.get(_normalize_brand_key(brand))

    def remember_domain(self, brand: str, domain: str) -> None:
        normalized = _normalize_domain(domain)
        if not normalized:
            return
        self.domain_memo[_normalize_brand_key(brand)] = normalized
