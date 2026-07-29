"""WeChat Official Account server callback (no JWT; signature verified)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from aperix_geo.api.deps import DbSession
from aperix_geo.config import get_settings
from aperix_geo.services.wechat.bind_ticket import complete_bind_from_scan
from aperix_geo.services.wechat.callback import (
    event_fields,
    maybe_decrypt_message,
    parse_callback_xml,
    verify_callback_signature,
)
from aperix_geo.services.wechat.config import wechat_configured

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wechat", tags=["wechat"])


@router.get("/callback")
def wechat_callback_verify(
    signature: str = Query(default=""),
    timestamp: str = Query(default=""),
    nonce: str = Query(default=""),
    echostr: str = Query(default=""),
) -> Response:
    settings = get_settings()
    if not wechat_configured(settings):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="WeChat MP not configured")
    ok = verify_callback_signature(
        token=settings.wechat_token,
        signature=signature,
        timestamp=timestamp,
        nonce=nonce,
    )
    if not ok:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")
    return Response(content=echostr, media_type="text/plain")


@router.post("/callback")
async def wechat_callback(request: Request, db: DbSession) -> Response:
    settings = get_settings()
    if not wechat_configured(settings):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="WeChat MP not configured")

    params = request.query_params
    signature = params.get("msg_signature") or params.get("signature") or ""
    timestamp = params.get("timestamp") or ""
    nonce = params.get("nonce") or ""
    body = await request.body()

    try:
        fields = parse_callback_xml(body)
    except Exception as exc:
        logger.warning("WeChat MP callback XML parse failed: %s", exc)
        return Response(content="success", media_type="text/plain")

    encrypt = fields.get("Encrypt")
    sig_ok = verify_callback_signature(
        token=settings.wechat_token,
        signature=signature,
        timestamp=timestamp,
        nonce=nonce,
        encrypt=encrypt if encrypt else None,
    )
    # 明文模式微信用 signature（不含 Encrypt）；安全模式用 msg_signature
    if not sig_ok and encrypt:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")
    if not sig_ok and not encrypt:
        # 兼容：部分环境下仍带 signature
        if not verify_callback_signature(
            token=settings.wechat_token,
            signature=params.get("signature") or "",
            timestamp=timestamp,
            nonce=nonce,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid signature")

    try:
        msg = maybe_decrypt_message(fields, settings=settings)
    except ValueError as exc:
        logger.warning("WeChat MP decrypt failed: %s", exc)
        return Response(content="success", media_type="text/plain")

    meta = event_fields(msg)
    if (meta.get("msg_type") or "").lower() == "event" and meta.get("ticket_id") and meta.get("open_id"):
        try:
            complete_bind_from_scan(
                db,
                ticket_id=str(meta["ticket_id"]),
                open_id=str(meta["open_id"]),
                settings=settings,
            )
        except Exception:
            logger.exception("WeChat MP bind from scan failed")

    # 必须快速返回 success，避免微信重试
    return Response(content="success", media_type="text/plain")
