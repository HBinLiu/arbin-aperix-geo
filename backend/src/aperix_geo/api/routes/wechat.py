"""WeChat Official Account: message callback + OAuth bind callback (no JWT)."""

from __future__ import annotations

import html
import logging

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse

from aperix_geo.api.deps import DbSession
from aperix_geo.config import get_settings
from aperix_geo.services.wechat.bind_ticket import complete_bind, complete_bind_from_scan
from aperix_geo.services.wechat.callback import (
    event_fields,
    maybe_decrypt_message,
    parse_callback_xml,
    verify_callback_signature,
)
from aperix_geo.services.wechat.config import wechat_configured, wechat_oauth_configured
from aperix_geo.services.wechat.oauth import exchange_oauth_code
from aperix_geo.services.wechat.token import WechatError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/wechat", tags=["wechat"])


def _oauth_result_html(*, title: str, message: str, ok: bool) -> str:
    color = "#1677ff" if ok else "#cf1322"
    safe_title = html.escape(title)
    safe_msg = html.escape(message)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{safe_title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           margin: 0; padding: 48px 24px; text-align: center; color: #1f1f1f; background: #f5f5f5; }}
    .card {{ max-width: 360px; margin: 0 auto; background: #fff; border-radius: 12px;
             padding: 32px 24px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
    h1 {{ font-size: 20px; margin: 0 0 12px; color: {color}; }}
    p {{ font-size: 15px; line-height: 1.6; margin: 0; color: #595959; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{safe_title}</h1>
    <p>{safe_msg}</p>
  </div>
</body>
</html>"""


@router.get("/oauth/callback", response_class=HTMLResponse)
def wechat_oauth_callback(
    db: DbSession,
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
    error_description: str = Query(default=""),
) -> HTMLResponse:
    """Webpage OAuth redirect target: exchange code, bind account, show result in WeChat."""
    settings = get_settings()
    if not wechat_oauth_configured(settings):
        return HTMLResponse(
            content=_oauth_result_html(
                title="暂不可用",
                message="微信网页授权未配置，请联系管理员。",
                ok=False,
            ),
            status_code=503,
        )

    if error.strip():
        detail = error_description.strip() or error.strip()
        return HTMLResponse(
            content=_oauth_result_html(title="授权已取消", message=detail or "未完成授权", ok=False),
        )

    ticket_id = state.strip()
    if not code.strip() or not ticket_id:
        return HTMLResponse(
            content=_oauth_result_html(
                title="绑定失败",
                message="缺少授权参数，请返回控制台重新扫码。",
                ok=False,
            ),
        )

    try:
        info = exchange_oauth_code(code, settings=settings)
        ticket = complete_bind(
            db,
            ticket_id=ticket_id,
            open_id=info.open_id,
            nick_name=info.nick_name,
            union_id=info.union_id,
        )
    except WechatError as exc:
        logger.warning("WeChat OAuth bind failed: %s", exc)
        return HTMLResponse(
            content=_oauth_result_html(title="绑定失败", message=str(exc), ok=False),
        )
    except Exception:
        logger.exception("WeChat OAuth bind unexpected error")
        return HTMLResponse(
            content=_oauth_result_html(
                title="绑定失败",
                message="服务异常，请稍后在控制台重试。",
                ok=False,
            ),
        )

    if ticket is None or ticket.status == "expired":
        return HTMLResponse(
            content=_oauth_result_html(
                title="二维码已过期",
                message="请返回控制台关闭弹窗后重新打开绑定。",
                ok=False,
            ),
        )
    if ticket.status == "failed":
        return HTMLResponse(
            content=_oauth_result_html(
                title="绑定失败",
                message=ticket.error or "无法完成绑定",
                ok=False,
            ),
        )
    if ticket.status == "bound":
        nick = (info.nick_name or "微信用户").strip()
        return HTMLResponse(
            content=_oauth_result_html(
                title="绑定成功",
                message=f"已绑定为「{nick}」。可返回控制台继续操作。",
                ok=True,
            ),
        )

    return HTMLResponse(
        content=_oauth_result_html(title="绑定未完成", message="请返回控制台查看状态。", ok=False),
    )


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

    # Legacy SCAN/subscribe bind (no nickname). Prefer /oauth/callback.
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
