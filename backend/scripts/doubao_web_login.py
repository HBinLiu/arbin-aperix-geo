#!/usr/bin/env python3
"""Headed login helper: open Doubao chat, wait for manual login, save storage_state.

Doubao shows a composer (and some cookies like odin_tt) even when logged out.
This script NEVER auto-closes on cookie heuristics — you must press Enter after
finishing login. It then verifies real session cookies before saving.

Usage (from backend/):

  export PYTHONPATH=src
  python3 scripts/doubao_web_login.py [--out data/doubao_storage_state.json]
"""

from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aperix_geo.services.providers.doubao_web.accounts import save_storage_state  # noqa: E402
from aperix_geo.services.providers.doubao_web.selectors import CHAT_URL  # noqa: E402

# Strong signals only. Do NOT include odin_tt / ttwid — those appear for guests.
_SESSION_COOKIE_NAMES = frozenset(
    {
        "sessionid",
        "sessionid_ss",
        "sid_guard",
        "sid_tt",
        "uid_tt",
        "uid_tt_ss",
    }
)


def _session_cookie_names(state: dict) -> list[str]:
    cookies = state.get("cookies") or []
    found: list[str] = []
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        name = str(cookie.get("name") or "")
        value = str(cookie.get("value") or "").strip()
        if name in _SESSION_COOKIE_NAMES and value:
            found.append(name)
    return sorted(set(found))


def main() -> int:
    parser = argparse.ArgumentParser(description="Save Doubao Playwright storage_state after manual login")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "data" / "doubao_storage_state.json",
        help="Output storage_state JSON path",
    )
    parser.add_argument("--url", default=CHAT_URL)
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed; pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    print(f"Opening {args.url}")
    print("1) 在弹出的浏览器里完成登录（手机号/验证码或扫码）")
    print("2) 确认页面已进入对话（能看到头像/个人入口，而不是「登录」按钮）")
    print("3) 回到本终端，按 Enter 才会保存并关闭浏览器")
    print("（浏览器会一直开着，直到你按 Enter 或 Ctrl+C）", flush=True)

    enter_event = threading.Event()

    def _wait_enter() -> None:
        try:
            input()
        except EOFError:
            pass
        enter_event.set()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context(locale="zh-CN", viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto(args.url, wait_until="domcontentloaded")

        waiter = threading.Thread(target=_wait_enter, daemon=True)
        waiter.start()

        try:
            while not enter_event.wait(timeout=2.0):
                # Keep the Playwright driver alive; show weak progress only.
                names = {str(c.get("name") or "") for c in (context.storage_state().get("cookies") or [])}
                session = _session_cookie_names(context.storage_state())
                if session:
                    print(f"  …已看到会话 Cookie {', '.join(session)}，登录完成后请按 Enter 保存", flush=True)
                elif "odin_tt" in names:
                    print("  …页面已加载（odin_tt 不算登录），请继续登录，完成后按 Enter", flush=True)
                else:
                    print("  …等待你在浏览器登录，完成后按 Enter", flush=True)
        except KeyboardInterrupt:
            print("\n已取消，未保存", file=sys.stderr)
            browser.close()
            return 130

        # Let late cookies settle after login UI closes.
        time.sleep(1.5)
        state = context.storage_state()
        session = _session_cookie_names(state)
        if not session:
            print(
                "按 Enter 后仍未检测到 sessionid / sid_guard / uid_tt 等会话 Cookie。\n"
                "浏览器会保持打开；请确认已真正登录后再重新运行本脚本。",
                file=sys.stderr,
            )
            cookie_names = sorted(
                {str(c.get("name") or "") for c in (state.get("cookies") or []) if isinstance(c, dict)}
            )
            print(f"当前 Cookie 名: {', '.join(cookie_names) or '(无)'}", file=sys.stderr)
            browser.close()
            return 3

        save_storage_state(args.out, state)
        print(f"Saved storage_state → {args.out}")
        print(f"会话 Cookie: {', '.join(session)}")
        print(f"Set DOUBAO_CRAWL_STORAGE_STATE_PATH={args.out}")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
