#!/usr/bin/env python3
"""Spike: Doubao Web HTTP completion via geo-web-crawl (mode=http) or sign-only.

Does NOT go through OpenAI-compatible APIs. Prints field inventory for Phase 1 gate.

Usage (from backend/):

  export PYTHONPATH=src
  export DOUBAO_CRAWL_STORAGE_STATE_PATH=data/doubao_storage_state.json
  # optional resident crawl service:
  # export GEO_WEB_CRAWL_BASE_URL=http://127.0.0.1:9410
  # export GEO_WEB_CRAWL_TOKEN=...

  python3 scripts/doubao_web_http_spike.py --prompt "推荐几个适合露营的帐篷"
  python3 scripts/doubao_web_http_spike.py --sign-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aperix_geo.config import get_settings  # noqa: E402
from aperix_geo.services.providers.doubao_web.accounts import (  # noqa: E402
    load_storage_state_from_file,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Doubao Web HTTP / sign spike")
    parser.add_argument("--prompt", default="用一句话介绍你自己")
    parser.add_argument(
        "--sign-only",
        action="store_true",
        help="Only exercise mode=sign (frontierSign), no completion",
    )
    parser.add_argument(
        "--via",
        choices=("browser", "httpx"),
        default="browser",
        help="Completion path (default: browser in-page fetch)",
    )
    args = parser.parse_args()

    settings = get_settings().model_copy(
        update={
            "doubao_web_http_enabled": True,
            "doubao_web_http_via": args.via,
        }
    )

    state = load_storage_state_from_file(settings)
    if state is None:
        print("FAIL: set DOUBAO_CRAWL_STORAGE_STATE_PATH to a valid storage_state JSON")
        return 2

    if args.sign_only:
        from aperix_geo.services.providers.doubao_web.web_http.client import request_a_bogus
        from urllib.parse import urlencode

        params = {
            "aid": "497858",
            "device_platform": "web",
            "language": "zh",
            "samantha_web": "1",
            "version_code": "20800",
        }
        try:
            job = request_a_bogus(storage_state=state, settings=settings, params=params)
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL sign: {type(exc).__name__}: {exc}")
            return 1
        print(
            json.dumps(
                {
                    "ok": True,
                    "a_bogus_len": len(str(job.get("a_bogus") or "")),
                    "fingerprint_keys": sorted((job.get("fingerprint") or {}).keys()),
                    "query_string": job.get("query_string") or urlencode(params),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    from aperix_geo.services.providers.doubao_web.web_http.client import complete_web_http

    try:
        job = complete_web_http(prompt=args.prompt, storage_state=state, settings=settings)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL web_http: {type(exc).__name__}: {exc}")
        return 1

    text = str(job.get("text") or "")
    summary = {
        "ok": bool(job.get("ok")),
        "text_len": len(text),
        "text_preview": text[:240],
        "conversation_id": job.get("conversation_id") or "",
        "search_queries": job.get("search_queries") or [],
        "source_urls": job.get("source_urls") or [],
        "has_share_url": False,
        "note": "share_url is filled only on hybrid path (mode=share)",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not text.strip():
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
