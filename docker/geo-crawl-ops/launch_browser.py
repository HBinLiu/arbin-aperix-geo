#!/usr/bin/env python3
"""Launch headed Chromium on DISPLAY with a persistent user-data-dir + CDP.

The Doubao session lives in GEO_CRAWL_OPS_PROFILE_DIR (same directory crawl uses).
Do not inject storage_state JSON from another Chrome — that is what from_logout=1 is.

Periodically dumps storage_state to ``/tmp/ops-live-storage-state.json`` so
watch_login can complete tickets.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import time
from pathlib import Path

LIVE_STATE_PATH = Path(
    (os.environ.get("GEO_CRAWL_OPS_LIVE_STATE_PATH") or "/tmp/ops-live-storage-state.json").strip()
)


def _log(msg: str) -> None:
    print(f"[geo-crawl-ops-launch] {msg}", flush=True)


def _dump_live_state(context: object) -> int:
    """Write storage_state JSON; return cookie count (best-effort)."""
    try:
        state = context.storage_state()  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        _log(f"live state dump failed: {exc}")
        return -1
    if not isinstance(state, dict):
        return -1
    cookies = state.get("cookies") if isinstance(state.get("cookies"), list) else []
    tmp = LIVE_STATE_PATH.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        tmp.replace(LIVE_STATE_PATH)
    except OSError as exc:
        _log(f"live state write failed: {exc}")
        return -1
    return len(cookies)


def _launch_args(cdp_port: int) -> list[str]:
    # Same flags as the pre-refactor headed session (Debian Chromium + Xvfb).
    # Playwright's bundled Chrome + SwiftShader crashed on keyboard input.
    return [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--window-size=1440,900",
        f"--remote-debugging-port={cdp_port}",
        "--remote-debugging-address=127.0.0.1",
    ]


def _chrome_executable() -> str | None:
    raw = (os.environ.get("GEO_CRAWL_OPS_CHROME_BIN") or "/usr/bin/chromium").strip()
    return raw if raw and Path(raw).exists() else None


def _clear_chrome_singleton_locks(profile_dir: Path) -> None:
    """docker rm -f leaves SingletonLock; next VNC Chromium then fails → black Xvfb."""
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        path = profile_dir / name
        try:
            if path.is_symlink() or path.exists():
                path.unlink()
                _log(f"removed leftover {name}")
        except OSError as exc:
            _log(f"could not remove {name}: {exc}")


def main() -> int:
    os.environ.setdefault("DISPLAY", ":1")
    start_url = (os.environ.get("GEO_CRAWL_OPS_START_URL") or "https://www.doubao.com/chat/").strip()
    profile_dir = (os.environ.get("GEO_CRAWL_OPS_PROFILE_DIR") or "").strip()
    cdp_port = int(os.environ.get("GEO_CRAWL_OPS_CDP_PORT") or "9222")
    dump_every_s = float(os.environ.get("GEO_CRAWL_OPS_LIVE_STATE_EVERY_S") or "2")

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

    if not profile_dir:
        _log("GEO_CRAWL_OPS_PROFILE_DIR unset; refusing ephemeral Chrome (would from_logout)")
        return 1
    profile_path = Path(profile_dir)
    profile_path.mkdir(parents=True, exist_ok=True)
    _clear_chrome_singleton_locks(profile_path)

    with sync_playwright() as playwright:
        chrome = _chrome_executable()
        _log(
            f"launch_persistent_context dir={profile_dir} cdp={cdp_port} "
            f"display={os.environ.get('DISPLAY')} chrome={chrome or 'playwright'}"
        )
        try:
            context = playwright.chromium.launch_persistent_context(
                str(profile_path),
                executable_path=chrome,
                headless=False,
                locale="zh-CN",
                viewport={"width": 1440, "height": 900},
                args=_launch_args(cdp_port),
            )
        except Exception as exc:  # noqa: BLE001
            _log(f"chromium launch failed: {exc}")
            return 1
        page = context.pages[0] if context.pages else context.new_page()
        try:
            page.goto(start_url, wait_until="domcontentloaded", timeout=120_000)
        except Exception as exc:  # noqa: BLE001
            _log(f"goto warning: {exc}")
        _log(f"browser ready cdp=127.0.0.1:{cdp_port} url={page.url} live={LIVE_STATE_PATH}")

        last_dump = 0.0
        last_logged_n = -2
        while not stop:
            now = time.monotonic()
            if now - last_dump >= max(0.5, dump_every_s):
                last_dump = now
                n = _dump_live_state(context)
                if n != last_logged_n and n >= 0:
                    _log(f"live state cookies={n}")
                    last_logged_n = n
            time.sleep(0.5)
            try:
                if not context.pages:
                    _log("browser pages gone")
                    break
            except Exception:
                _log("browser disconnected")
                break

        try:
            _dump_live_state(context)
        except Exception:
            pass
        try:
            context.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
