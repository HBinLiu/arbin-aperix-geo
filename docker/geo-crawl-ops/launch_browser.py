#!/usr/bin/env python3
"""Launch headed Chromium on DISPLAY with optional Playwright storage_state + CDP."""

from __future__ import annotations

import json
import os
import signal
import sys
import time
from pathlib import Path


def _log(msg: str) -> None:
    print(f"[geo-crawl-ops-launch] {msg}", flush=True)


def main() -> int:
    start_url = (os.environ.get("GEO_CRAWL_OPS_START_URL") or "https://www.doubao.com/chat/").strip()
    state_path = (os.environ.get("GEO_CRAWL_OPS_STORAGE_STATE_PATH") or "").strip()
    cdp_port = int(os.environ.get("GEO_CRAWL_OPS_CDP_PORT") or "9222")
    chrome = (os.environ.get("GEO_CRAWL_OPS_CHROME_BIN") or "/usr/bin/chromium").strip()

    storage_state = None
    if state_path and Path(state_path).is_file():
        try:
            raw = json.loads(Path(state_path).read_text(encoding="utf-8"))
            if isinstance(raw, dict) and isinstance(raw.get("cookies"), list) and raw["cookies"]:
                storage_state = raw
                _log(f"loading storage_state cookies={len(raw['cookies'])} from {state_path}")
            else:
                _log(f"storage_state unusable at {state_path}; starting clean")
        except (OSError, json.JSONDecodeError) as exc:
            _log(f"storage_state read failed: {exc}; starting clean")
    else:
        _log("no storage_state; starting clean browser")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _log("playwright missing")
        return 1

    stop = False

    def _stop(*_args: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=chrome if Path(chrome).exists() else None,
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1440,900",
                f"--remote-debugging-port={cdp_port}",
                "--remote-debugging-address=127.0.0.1",
            ],
        )
        context = browser.new_context(
            storage_state=storage_state,
            locale="zh-CN",
            viewport={"width": 1440, "height": 900},
        )
        page = context.new_page()
        try:
            page.goto(start_url, wait_until="domcontentloaded", timeout=120_000)
        except Exception as exc:  # noqa: BLE001
            _log(f"goto warning: {exc}")
        _log(f"browser ready cdp=127.0.0.1:{cdp_port} url={page.url}")

        while not stop:
            time.sleep(1.0)
            if not browser.is_connected():
                _log("browser disconnected")
                break

        try:
            browser.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
