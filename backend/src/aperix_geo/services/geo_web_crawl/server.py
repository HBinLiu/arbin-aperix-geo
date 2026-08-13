"""Resident FastAPI server for geo-web-crawl."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Body, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from aperix_geo.services.geo_web_crawl.browser_pool import browser_backend
from aperix_geo.services.geo_web_crawl.jobs import shutdown_executor, submit_job
from aperix_geo.services.geo_web_crawl.registry import ensure_handlers_loaded, list_platforms

logger = logging.getLogger(__name__)


class JobRequest(BaseModel):
    platform: str = "doubao"
    mode: str = "crawl"
    storage_state: dict[str, Any]
    prompt: str = ""
    timeout_s: float = Field(default=120.0, ge=10.0, le=900.0)
    headless: bool = True
    chat_base_url: str = ""

    model_config = {"extra": "allow"}


def _expected_token() -> str:
    return (os.environ.get("GEO_WEB_CRAWL_TOKEN") or "").strip()


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
            "concurrency": int(os.environ.get("GEO_WEB_CRAWL_CONCURRENCY") or "2"),
            "browser_backend": browser_backend(),
        }

    @app.post("/v1/jobs")
    def create_job(
        payload: Annotated[JobRequest, Body()],
        authorization: str | None = Header(default=None),
        x_geo_web_crawl_token: str | None = Header(
            default=None, alias="X-Geo-Web-Crawl-Token"
        ),
    ) -> dict[str, Any]:
        expected = _expected_token()
        if expected:
            got = ""
            if authorization and authorization.lower().startswith("bearer "):
                got = authorization[7:].strip()
            elif x_geo_web_crawl_token:
                got = x_geo_web_crawl_token.strip()
            if got != expected:
                raise HTTPException(status_code=401, detail="invalid crawl token")

        body = payload.model_dump()
        logger.info(
            "geo-web-crawl job platform=%s mode=%s timeout_s=%s",
            body.get("platform"),
            body.get("mode"),
            body.get("timeout_s"),
        )
        return submit_job(body)

    return app


app = create_app()
