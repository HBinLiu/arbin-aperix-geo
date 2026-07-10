"""Billing and subscription routes."""

import secrets
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response

from sqlalchemy import select

from aperix_geo.api.deps import CurrentUser, DbSession
from aperix_geo.config import get_settings
from aperix_geo.db.models import EPOCH, Plan, ZERO_UUID
from aperix_geo.schemas.billing import (
    BillingCycleOptionOut,
    CreateSubscriptionOrderIn,
    CreateUsagePackOrderIn,
    PaymentWebhookIn,
    PaymentWebhookOut,
    PayOrderListIn,
    PayOrderListItemOut,
    PayOrderListOut,
    PayOrderOut,
    PayOrderPrepayOut,
    PlanCatalogItemOut,
    PlanCatalogOut,
    PlanLimitItemOut,
    PlanLimitsOut,
    PlanPriceOut,
    QuotaRecordExportIn,
    QuotaRecordFiltersOut,
    QuotaRecordListIn,
    QuotaRecordListItemOut,
    QuotaRecordListOut,
    QuotaRecordTypeFilterOptionOut,
    SubscriptionOut,
    UsagePackCatalogItemOut,
    UsagePackCatalogOut,
    UsageOut,
)
from aperix_geo.services.auth.otp import is_dev_environment
from aperix_geo.services.billing.ledger import usage_pack_product_label
from aperix_geo.services.billing.plan_catalog import PlanCatalog, get_plan_catalog
from aperix_geo.services.billing.usage_catalog import get_usage_pack_catalog
from aperix_geo.services.billing.exceptions import SubscriptionInactiveError
from aperix_geo.services.billing.orders import (
    cancel_tenant_pay_order,
    create_subscription_order,
    create_usage_pack_order,
    get_pay_order_by_id,
    get_tenant_pay_order,
    list_tenant_pay_orders_paginated,
)
from aperix_geo.services.billing.payments import fulfill_paid_order
from aperix_geo.services.billing.quota import get_subscription_snapshot
from aperix_geo.services.billing.quota_records import (
    QuotaRecordRow,
    export_tenant_quota_records_csv,
    list_tenant_quota_records_paginated,
    quota_record_filter_options,
)
from aperix_geo.services.billing.wechat_pay import (
    WechatPayError,
    create_native_prepay,
    handle_wechat_notification,
    is_wechat_pay_configured,
)

router = APIRouter(prefix="/billing", tags=["billing"])


def _verify_webhook_secret(provided: str | None) -> None:
    expected = get_settings().billing_pay_webhook_secret.strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment webhook is not configured",
        )
    if not provided or provided.strip() != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")


def _order_plan_code(db, order) -> str | None:
    if order.plan_id == ZERO_UUID:
        return None
    plan = db.get(Plan, order.plan_id)
    return plan.code if plan is not None else None


@router.get("/orders/{order_id}", response_model=PayOrderOut)
def get_tenant_pay_order_route(
    order_id: UUID,
    current: CurrentUser,
    db: DbSession,
) -> PayOrderOut:
    try:
        order = get_tenant_pay_order(db, tenant_id=current.tenant_id, order_id=order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _order_to_out(order, plan_code=_order_plan_code(db, order))


@router.post("/orders/{order_id}/pay", response_model=PayOrderPrepayOut)
def prepay_tenant_pay_order_route(
    order_id: UUID,
    current: CurrentUser,
    db: DbSession,
) -> PayOrderPrepayOut:
    settings = get_settings()
    try:
        order = get_tenant_pay_order(db, tenant_id=current.tenant_id, order_id=order_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if order.status == "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order is already paid")
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order cannot be paid in status: {order.status}",
        )

    if not is_wechat_pay_configured(settings):
        if is_dev_environment(settings):
            return PayOrderPrepayOut(
                order_id=order.id,
                amount_cents=order.amount_cents,
                mode="dev",
                code_url=None,
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WeChat Pay is not configured",
        )

    try:
        code_url = create_native_prepay(order, settings=settings)
    except WechatPayError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return PayOrderPrepayOut(
        order_id=order.id,
        amount_cents=order.amount_cents,
        mode="wechat_native",
        code_url=code_url,
    )


@router.post("/orders/{order_id}/simulate-pay", response_model=PayOrderOut)
def simulate_tenant_pay_order_route(
    order_id: UUID,
    current: CurrentUser,
    db: DbSession,
) -> PayOrderOut:
    settings = get_settings()
    if not is_dev_environment(settings):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Simulated payment is only available in development",
        )
    try:
        get_tenant_pay_order(db, tenant_id=current.tenant_id, order_id=order_id)
        order = fulfill_paid_order(
            db,
            order_id,
            payment_id=f"dev_{secrets.token_hex(8)}",
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _order_to_out(order, plan_code=_order_plan_code(db, order))


def _plan_catalog_to_out(catalog: PlanCatalog) -> PlanCatalogOut:
    return PlanCatalogOut(
        plans=[
            PlanCatalogItemOut(
                code=plan.code,
                name=plan.name,
                description=plan.description,
                orderable=plan.orderable,
                limits=[
                    PlanLimitItemOut(
                        key=limit.key,
                        label=limit.label,
                        description=limit.description,
                        value=limit.value,
                        comparison_only=limit.comparison_only,
                    )
                    for limit in plan.limits
                ],
                prices=[
                    PlanPriceOut(
                        billing_cycle=price.billing_cycle,
                        monthly_cents=price.monthly_cents,
                        period_total_cents=price.period_total_cents,
                        discount_badge=price.discount_badge,
                    )
                    for price in plan.prices
                ],
            )
            for plan in catalog.plans
        ],
        billing_cycles=[
            BillingCycleOptionOut(id=cycle.id, label=cycle.label, badge=cycle.badge)
            for cycle in catalog.billing_cycles
        ],
    )


@router.get("/plans", response_model=PlanCatalogOut)
def list_subscription_plans(db: DbSession) -> PlanCatalogOut:
    return _plan_catalog_to_out(get_plan_catalog(db))


@router.get("/usage-packs", response_model=UsagePackCatalogOut)
def list_usage_packs(current: CurrentUser, db: DbSession) -> UsagePackCatalogOut:
    del current
    catalog = get_usage_pack_catalog(db)
    return UsagePackCatalogOut(
        packs=[
            UsagePackCatalogItemOut(
                code=pack.code,
                title=pack.title,
                order_label=pack.order_label,
                quantity=pack.quantity,
                price_cents=pack.price_cents,
                unit_price_cents=pack.unit_price_cents,
            )
            for pack in catalog.packs
        ]
    )


@router.get("/subscription", response_model=SubscriptionOut)
def get_tenant_subscription(current: CurrentUser, db: DbSession) -> SubscriptionOut:
    try:
        snapshot = get_subscription_snapshot(db, current.tenant_id)
    except SubscriptionInactiveError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return SubscriptionOut(
        tenant_id=current.tenant_id,
        plan_code=snapshot.plan_code,
        plan_name=snapshot.plan_name,
        billing_cycle=snapshot.billing_cycle,
        status=snapshot.status,
        current_period_start=snapshot.current_period_start,
        current_period_end=snapshot.current_period_end,
        ai_period_start=snapshot.ai_period_start,
        ai_period_end=snapshot.ai_period_end,
        subscription_active=snapshot.subscription_active,
        limits=PlanLimitsOut(
            max_subjects=snapshot.limits.max_subjects,
            max_per_platforms=snapshot.limits.max_per_platforms,
            max_per_competitors=snapshot.limits.max_per_competitors,
            max_prompts_total=snapshot.limits.max_prompts_total,
            per_month_usages=snapshot.limits.per_month_usages,
            max_team_members=snapshot.limits.max_team_members,
            sampling_frequency=snapshot.limits.sampling_frequency,
        ),
        usage=UsageOut(
            subjects_count=snapshot.usage.subjects_count,
            prompts_count=snapshot.usage.prompts_count,
            monthly_limit=snapshot.usage.monthly_limit,
            monthly_used=snapshot.usage.monthly_used,
            monthly_remaining=snapshot.usage.monthly_remaining,
            usage_pack_balance=snapshot.usage.usage_pack_balance,
            ai_requests_available=snapshot.usage.ai_requests_available,
        ),
    )


def _order_to_out(order, *, plan_code: str | None = None) -> PayOrderOut:
    return PayOrderOut(
        id=order.id,
        order_type=order.order_type,
        amount_cents=order.amount_cents,
        status=order.status,
        plan_code=plan_code,
        billing_cycle=order.billing_cycle or None,
        product_code=order.product_code or None,
        quantity=order.quantity or None,
    )


def _orders_to_list_out(db, orders) -> list[PayOrderListItemOut]:
    plan_ids = {order.plan_id for order in orders if order.plan_id != ZERO_UUID}
    plan_map: dict = {}
    if plan_ids:
        rows = db.execute(select(Plan).where(Plan.id.in_(plan_ids))).scalars().all()
        plan_map = {plan.id: plan for plan in rows}

    items: list[PayOrderListItemOut] = []
    for order in orders:
        plan = plan_map.get(order.plan_id)
        paid_at = order.paid_at if order.paid_at and order.paid_at != EPOCH else None
        product_code = order.product_code or None
        product_label = None
        if product_code:
            product_label = usage_pack_product_label(product_code, quantity=order.quantity or 0)
        items.append(
            PayOrderListItemOut(
                id=order.id,
                order_type=order.order_type,
                amount_cents=order.amount_cents,
                status=order.status,
                created_at=order.created_at,
                paid_at=paid_at,
                plan_code=plan.code if plan else None,
                plan_name=plan.name if plan else None,
                billing_cycle=order.billing_cycle or None,
                product_code=product_code,
                product_label=product_label,
                quantity=order.quantity or None,
            )
        )
    return items


@router.post("/orders", response_model=PayOrderListOut)
def list_tenant_pay_orders_route(
    body: PayOrderListIn,
    current: CurrentUser,
    db: DbSession,
) -> PayOrderListOut:
    orders, total, safe_page, safe_page_size = list_tenant_pay_orders_paginated(
        db,
        current.tenant_id,
        page=body.page,
        page_size=body.page_size,
        sort_by=body.sort_by,
        order=body.order,
    )
    return PayOrderListOut(
        items=_orders_to_list_out(db, orders),
        total=total,
        page=safe_page,
        page_size=safe_page_size,
    )


@router.post("/orders/{order_id}/cancel", response_model=PayOrderOut)
def cancel_tenant_pay_order_route(
    order_id: UUID,
    current: CurrentUser,
    db: DbSession,
) -> PayOrderOut:
    try:
        order = cancel_tenant_pay_order(db, tenant_id=current.tenant_id, order_id=order_id)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    plan_code: str | None = None
    if order.plan_id != ZERO_UUID:
        plan = db.get(Plan, order.plan_id)
        plan_code = plan.code if plan is not None else None
    return _order_to_out(order, plan_code=plan_code)


def _quota_record_rows_to_out(rows: list[QuotaRecordRow]) -> list[QuotaRecordListItemOut]:
    return [
        QuotaRecordListItemOut(
            id=row.id,
            created_at=row.created_at,
            record_type=row.record_type,
            record_type_label=row.record_type_label,
            source=row.source,
            source_label=row.source_label,
            amount_delta=row.amount_delta,
            subject_id=row.subject_id,
            subject_brand=row.subject_brand,
        )
        for row in rows
    ]


def _quota_record_filters_out() -> QuotaRecordFiltersOut:
    meta = quota_record_filter_options()
    return QuotaRecordFiltersOut(
        days=list(meta.days),
        record_types=[
            QuotaRecordTypeFilterOptionOut(value=value, label=label)
            for value, label in meta.record_types
        ],
        default_days=meta.default_days,
    )


@router.get("/quota-records/filters", response_model=QuotaRecordFiltersOut)
def list_tenant_quota_record_filters_route(
    current: CurrentUser,
) -> QuotaRecordFiltersOut:
    del current
    return _quota_record_filters_out()


@router.post("/quota-records", response_model=QuotaRecordListOut)
def list_tenant_quota_records_route(
    body: QuotaRecordListIn,
    current: CurrentUser,
    db: DbSession,
) -> QuotaRecordListOut:
    rows, total, safe_page, safe_page_size = list_tenant_quota_records_paginated(
        db,
        current.tenant_id,
        page=body.page,
        page_size=body.page_size,
        sort_by=body.sort_by,
        order=body.order,
        days=body.days,
        record_type=body.record_type,
    )
    return QuotaRecordListOut(
        items=_quota_record_rows_to_out(rows),
        total=total,
        page=safe_page,
        page_size=safe_page_size,
    )


@router.post("/quota-records/export")
def export_tenant_quota_records_route(
    body: QuotaRecordExportIn,
    current: CurrentUser,
    db: DbSession,
) -> Response:
    csv_text = export_tenant_quota_records_csv(
        db,
        current.tenant_id,
        sort_by=body.sort_by,
        order=body.order,
        days=body.days,
        record_type=body.record_type,
    )
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="quota-records.csv"'},
    )


@router.post("/orders/subscription", response_model=PayOrderOut, status_code=status.HTTP_201_CREATED)
def create_subscription_pay_order(
    body: CreateSubscriptionOrderIn,
    current: CurrentUser,
    db: DbSession,
) -> PayOrderOut:
    try:
        order = create_subscription_order(
            db,
            tenant_id=current.tenant_id,
            user_id=current.id,
            plan_code=body.plan_code,
            billing_cycle=body.billing_cycle,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _order_to_out(order, plan_code=body.plan_code)


@router.post("/orders/usage-pack", response_model=PayOrderOut, status_code=status.HTTP_201_CREATED)
def create_usage_pack_pay_order(
    body: CreateUsagePackOrderIn,
    current: CurrentUser,
    db: DbSession,
) -> PayOrderOut:
    try:
        order = create_usage_pack_order(
            db,
            tenant_id=current.tenant_id,
            user_id=current.id,
            product_code=body.product_code,
            quantity=body.quantity,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _order_to_out(order)


@router.post("/webhook/payment", response_model=PaymentWebhookOut)
def payment_webhook(
    body: PaymentWebhookIn,
    db: DbSession,
    x_billing_webhook_secret: str | None = Header(default=None, alias="X-Billing-Webhook-Secret"),
) -> PaymentWebhookOut:
    _verify_webhook_secret(x_billing_webhook_secret)
    try:
        order = fulfill_paid_order(
            db,
            body.order_id,
            payment_id=body.payment_id,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PaymentWebhookOut(order_id=order.id, order_type=order.order_type, status=order.status)


@router.post("/webhook/wechat")
async def wechat_payment_webhook(request: Request, db: DbSession) -> JSONResponse:
    if not is_wechat_pay_configured():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"code": "FAIL", "message": "WeChat Pay is not configured"},
        )

    body = await request.body()
    try:
        result = handle_wechat_notification(
            body,
            signature=request.headers.get("Wechatpay-Signature", ""),
            timestamp=request.headers.get("Wechatpay-Timestamp", ""),
            nonce=request.headers.get("Wechatpay-Nonce", ""),
            serial=request.headers.get("Wechatpay-Serial", ""),
        )
        order = get_pay_order_by_id(db, result.order_id)
    except WechatPayError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"code": "FAIL", "message": str(exc)},
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"code": "FAIL", "message": str(exc)},
        )

    if order.amount_cents != result.amount_cents:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"code": "FAIL", "message": "Payment amount mismatch"},
        )

    try:
        fulfill_paid_order(db, result.order_id, payment_id=result.transaction_id)
        db.commit()
    except ValueError as exc:
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"code": "FAIL", "message": str(exc)},
        )

    return JSONResponse(content={"code": "SUCCESS", "message": "成功"})
