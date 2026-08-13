"""CLI entry for Doubao browser crawl in a fresh OS process (not Celery daemon child).

Prefer ``async_playwright`` (stable under Celery spawn). Sync Playwright is a fallback
only: its greenlet dispatcher often fails with
``PlaywrightContextManager has no attribute '_playwright'``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import queue
import sys
import threading
import traceback
from pathlib import Path
from typing import Any


def _fail(message: str, *, error_type: str = "DoubaoCrawlError") -> dict[str, Any]:
    return {
        "ok": False,
        "error_type": error_type,
        "error": message,
        "human_ops": False,
        "storage_state": None,
    }


def _write_result(out_path: Path, result: dict[str, Any]) -> None:
    out_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


def _clear_thread_event_loop() -> None:
    import asyncio as _asyncio

    try:
        _asyncio.set_event_loop(None)
    except Exception:
        pass


def _open_sync_browser(payload: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    """Return ``(playwright_cm, browser, context, page)`` — caller must close."""
    _clear_thread_event_loop()
    from playwright.sync_api import sync_playwright

    headless = bool(payload.get("headless", True))
    storage_state = payload.get("storage_state")
    if not isinstance(storage_state, dict):
        raise RuntimeError("storage_state missing")

    timeout_s = float(payload.get("timeout_s") or 120)
    timeout_ms = min(60_000, int(timeout_s * 1000))

    cm = sync_playwright()
    try:
        playwright = cm.__enter__()
    except AttributeError as exc:
        raise RuntimeError(
            "sync_playwright enter failed (AttributeError _playwright); "
            "check greenlet + `playwright install chromium`. "
            f"detail={exc!r}"
        ) from exc

    try:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context(
            storage_state=storage_state,
            locale="zh-CN",
            viewport={"width": 1440, "height": 900},
        )
        context.set_default_timeout(max(1_000, timeout_ms))
        try:
            context.grant_permissions(["clipboard-read", "clipboard-write"])
        except Exception:
            pass
        page = context.new_page()
        return cm, browser, context, page
    except Exception:
        try:
            cm.__exit__(*sys.exc_info())
        except Exception:
            pass
        raise


def _run_sync_job_on_thread(payload: dict[str, Any]) -> dict[str, Any]:
    """Start Playwright first, then import aperix and crawl — all on this thread."""
    _clear_thread_event_loop()
    cm = browser = context = None
    try:
        cm, browser, context, page = _open_sync_browser(payload)
        from aperix_geo.services.providers.doubao_web.browser_crawl_job import (
            run_doubao_browser_crawl_on_page,
        )

        return run_doubao_browser_crawl_on_page(page, context, payload)
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception("doubao-crawl-cli sync path failed")
        return _fail(f"{type(exc).__name__}: {exc}")
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                pass
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        if cm is not None:
            try:
                if getattr(cm, "_playwright", None) is not None or getattr(
                    cm, "_connection", None
                ) is not None:
                    cm.__exit__(None, None, None)
            except Exception:
                pass


def _run_sync_fallback(payload: dict[str, Any]) -> dict[str, Any]:
    result_q: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)

    def _worker() -> None:
        result_q.put(_run_sync_job_on_thread(payload))

    thread = threading.Thread(target=_worker, name="doubao-pw-sync", daemon=False)
    thread.start()
    timeout_s = float(payload.get("timeout_s") or 120) + 90.0
    thread.join(timeout=timeout_s)
    if thread.is_alive():
        return _fail(f"sync crawl thread timed out after {timeout_s:.0f}s")
    try:
        return result_q.get_nowait()
    except queue.Empty:
        return _fail("sync crawl thread exited without result")


def _run_async_primary(payload: dict[str, Any]) -> dict[str, Any]:
    logging.getLogger(__name__).info("doubao-crawl-cli: using async_playwright")
    try:
        from aperix_geo.services.providers.doubao_web.browser_crawl_async import (
            run_doubao_browser_crawl_job_async,
        )

        return asyncio.run(run_doubao_browser_crawl_job_async(payload))
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).exception("doubao-crawl-cli async path failed")
        return _fail(
            f"async_playwright failed: {type(exc).__name__}: {exc}\n"
            f"{traceback.format_exc()[-500:]}"
        )


def _run_job(payload: dict[str, Any]) -> dict[str, Any]:
    result = _run_async_primary(payload)
    if result.get("ok"):
        return result
    err = str(result.get("error") or "")
    # Retry once with sync-on-thread if async path looks like an env/driver issue.
    if any(
        token in err.lower()
        for token in ("executable doesn't exist", "browserType.launch", "async_playwright failed")
    ):
        logging.getLogger(__name__).warning(
            "doubao-crawl-cli: async path failed; trying sync Playwright thread"
        )
        return _run_sync_fallback(payload)
    return result


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Doubao Playwright crawl job (subprocess)")
    parser.add_argument("--in", dest="in_path", required=True, help="Input JSON payload path")
    parser.add_argument("--out", dest="out_path", required=True, help="Output JSON result path")
    args = parser.parse_args(argv)

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)
    try:
        payload = json.loads(in_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _write_result(out_path, _fail(f"invalid input payload: {exc}"))
        return 2

    if not isinstance(payload, dict):
        _write_result(out_path, _fail("payload must be a JSON object"))
        return 2

    result = _run_job(payload)
    _write_result(out_path, result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
