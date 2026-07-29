#!/usr/bin/env python3
"""Headed login helper: open Doubao chat, wait for manual login, save storage_state.

Usage (from backend/):

  export PYTHONPATH=src
  python3 scripts/doubao_web_login.py [--out data/doubao_storage_state.json] [--timeout-s 300]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aperix_geo.services.providers.doubao_web.accounts import save_storage_state  # noqa: E402
from aperix_geo.services.providers.doubao_web.selectors import CHAT_URL  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Save Doubao Playwright storage_state after manual login")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "doubao_storage_state.json",
        help="Output storage_state JSON path",
    )
    parser.add_argument("--timeout-s", type=int, default=300, help="Max seconds to wait for login")
    parser.add_argument("--url", default=CHAT_URL)
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed; pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    print(f"Opening {args.url} — please log in in the browser window…")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context(locale="zh-CN", viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto(args.url, wait_until="domcontentloaded")

        deadline = time.monotonic() + max(30, args.timeout_s)
        while time.monotonic() < deadline:
            url = (page.url or "").lower()
            # Heuristic: left login page and chat shell present.
            if "login" not in url and "passport" not in url:
                composer = page.locator("textarea, div[contenteditable='true']")
                if composer.count() > 0:
                    break
            time.sleep(2)
        else:
            print("Timed out waiting for login", file=sys.stderr)
            browser.close()
            return 2

        save_storage_state(args.out, context.storage_state())
        print(f"Saved storage_state → {args.out}")
        print(f"Set DOUBAO_CRAWL_STORAGE_STATE_PATH={args.out}")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
