"""Resident FastAPI server for crawl-browser."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Body, Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from aperix_geo.services.crawl_browser.browser_pool import (
    browser_backend,
    novnc_public_port,
    vnc_enabled,
)
from aperix_geo.services.crawl_browser.jobs import shutdown_executor, submit_job
from aperix_geo.services.crawl_browser.login_session import (
    LoginSessionError,
    login_session_status,
    parse_login_session_id,
    start_login_session,
    stop_login_session,
)
from aperix_geo.services.crawl_browser.registry import ensure_handlers_loaded, list_platforms

logger = logging.getLogger(__name__)


class JobRequest(BaseModel):
    platform: str = "doubao"
    mode: str = "crawl"
    account_id: str = ""
    storage_state: dict[str, Any] = Field(default_factory=dict)
    prompt: str = ""
    timeout_s: float = Field(default=120.0, ge=10.0, le=900.0)
    chat_base_url: str = ""

    model_config = {"extra": "allow"}


class LoginSessionRequest(BaseModel):
    account_id: str
    platform: str = "doubao"
    start_url: str = ""
    ticket_token: str = ""
    complete_url: str = ""
    ttl_min: int = Field(default=10, ge=5, le=120)
    captcha_clear_stable_s: float = Field(default=10.0, ge=5.0, le=600.0)
    reason: str = "login_expired"
    baseline_storage_state: dict[str, Any] = Field(default_factory=dict)


class LoginStopRequest(BaseModel):
    account_id: str = ""
    session_id: str = ""


def _expected_token() -> str:
    return (os.environ.get("GEO_WEB_CRAWL_TOKEN") or "").strip()


def _require_token(
    authorization: str | None = Header(default=None),
    x_geo_web_crawl_token: str | None = Header(
        default=None, alias="X-Geo-Web-Crawl-Token"
    ),
) -> None:
    expected = _expected_token()
    if not expected:
        return
    got = ""
    if authorization and authorization.lower().startswith("bearer "):
        got = authorization[7:].strip()
    elif x_geo_web_crawl_token:
        got = x_geo_web_crawl_token.strip()
    if got != expected:
        raise HTTPException(status_code=401, detail="invalid crawl token")


CrawlAuth = Annotated[None, Depends(_require_token)]


def create_app() -> FastAPI:
    ensure_handlers_loaded()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        shutdown_executor()

    app = FastAPI(title="Aperix GEO web-crawl", version="1.0.0", lifespan=lifespan)

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {
            "ok": True,
            "platforms": list_platforms(),
            "concurrency": int(os.environ.get("GEO_WEB_CRAWL_CONCURRENCY") or "1"),
            "browser_backend": browser_backend(),
            "vnc": vnc_enabled(),
            "vnc_port": novnc_public_port() if vnc_enabled() else 0,
        }

    @app.post("/v1/jobs")
    def create_job(
        payload: Annotated[JobRequest, Body()],
        _: CrawlAuth,
    ) -> dict[str, Any]:
        body = payload.model_dump()
        logger.info(
            "geo-web-crawl job platform=%s mode=%s account=%s timeout_s=%s",
            body.get("platform"),
            body.get("mode"),
            body.get("account_id") or "-",
            body.get("timeout_s"),
        )
        return submit_job(body)

    @app.post("/v1/login-sessions")
    def create_login_session(
        payload: Annotated[LoginSessionRequest, Body()],
        _: CrawlAuth,
    ) -> dict[str, Any]:
        try:
            info = start_login_session(
                account_id=payload.account_id,
                platform=payload.platform,
                start_url=payload.start_url,
                ticket_token=payload.ticket_token,
                complete_url=payload.complete_url,
                ttl_min=payload.ttl_min,
                captcha_clear_stable_s=payload.captcha_clear_stable_s,
                reason=payload.reason,
                baseline_storage_state=payload.baseline_storage_state or None,
            )
        except LoginSessionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {
            "ok": True,
            "account_id": info.account_id,
            "session_id": info.session_id,
            "watching": info.watching,
            "platform": info.platform,
            "reason": info.reason,
            "vnc_port": novnc_public_port() if vnc_enabled() else 0,
        }

    @app.get("/v1/login-sessions/{account_id}")
    def get_login_session(
        account_id: str,
        _: CrawlAuth,
    ) -> dict[str, Any]:
        info = login_session_status(account_id)
        if info is None or not info.watching:
            return {"ok": True, "watching": False, "account_id": account_id}
        return {
            "ok": True,
            "watching": True,
            "account_id": info.account_id,
            "session_id": info.session_id,
            "platform": info.platform,
            "reason": info.reason,
            "vnc_port": novnc_public_port() if vnc_enabled() else 0,
        }

    @app.post("/v1/login-sessions/stop")
    def stop_login(
        payload: Annotated[LoginStopRequest, Body()],
        _: CrawlAuth,
    ) -> dict[str, Any]:
        aid = (payload.account_id or "").strip() or parse_login_session_id(payload.session_id)
        if not aid:
            raise HTTPException(status_code=400, detail="account_id required")
        stopped = stop_login_session(aid)
        return {"ok": True, "account_id": aid, "stopped": stopped}

    return app


app = create_app()
