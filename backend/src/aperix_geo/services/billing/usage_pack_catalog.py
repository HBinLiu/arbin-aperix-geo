"""Usage pack catalog for purchase UI."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from aperix_geo.db.models import PlanPack
from aperix_geo.services.billing.constants import CUSTOM_USAGE_PACK_CODE


@dataclass(frozen=True)
class UsagePackCatalogItem:
    code: str
    title: str
    order_label: str
    quantity: int
    price_cents: int
    unit_price_cents: int


@dataclass(frozen=True)
class UsagePackCatalog:
    packs: tuple[UsagePackCatalogItem, ...]


def format_usage_pack_title(quantity: int) -> str:
    return f"{quantity:,} 次"


def format_usage_pack_order_label(product_code: str, *, quantity: int = 0) -> str:
    if product_code == CUSTOM_USAGE_PACK_CODE:
        if quantity > 0:
            return f"AI 配额包 {quantity:,}"
        return "AI 配额包（自定义）"
    if quantity > 0:
        return f"AI 配额包 {quantity:,}"
    return product_code


def get_usage_pack_catalog(db: Session) -> UsagePackCatalog:
    """Load fixed usage pack products available for self-service purchase."""
    products = list(
        db.execute(
            select(PlanPack)
            .where(
                PlanPack.is_active.is_(True),
                PlanPack.deleted.is_(False),
                PlanPack.code != CUSTOM_USAGE_PACK_CODE,
                PlanPack.quantity > 0,
                PlanPack.price_cents > 0,
            )
            .order_by(PlanPack.sort_order.asc(), PlanPack.code.asc())
        )
        .scalars()
        .all()
    )

    packs = tuple(
        UsagePackCatalogItem(
            code=product.code,
            title=format_usage_pack_title(product.quantity),
            order_label=format_usage_pack_order_label(product.code, quantity=product.quantity),
            quantity=product.quantity,
            price_cents=product.price_cents,
            unit_price_cents=product.unit_price_cents,
        )
        for product in products
    )
    return UsagePackCatalog(packs=packs)
