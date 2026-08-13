"""CLI entry for Doubao browser crawl in a fresh OS process (not Celery daemon child).

Async Playwright only — Sync API's greenlet dispatcher is broken in this deployment
path (``PlaywrightContextManager`` / ``_playwright``). Do not fall back to sync.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
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


def _playwright_install_hint(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}"
    lower = text.lower()
    if (
        "executable doesn't exist" in lower
        or "browsertype.launch" in lower
        or "playwright install" in lower
    ):
        return (
            f"{text}\n"
            "Hint: install browsers in the same venv as the worker, e.g.\n"
            "  python -m playwright install chromium\n"
            "  # or: playwright install --with-deps chromium"
        )
    return text


def _run_async_job(payload: dict[str, Any]) -> dict[str, Any]:
    log = logging.getLogger(__name__)
    log.info("doubao-crawl-cli: using async_playwright (sync disabled)")
    try:
        from aperix_geo.services.providers.doubao_web.browser_crawl_async import (
            run_doubao_browser_crawl_job_async,
        )

        return asyncio.run(run_doubao_browser_crawl_job_async(payload))
    except Exception as exc:  # noqa: BLE001
        log.exception("doubao-crawl-cli async path failed")
        return _fail(
            "async_playwright failed: "
            f"{_playwright_install_hint(exc)}\n"
            f"{traceback.format_exc()[-800:]}"
        )


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

    result = _run_async_job(payload)
    if not result.get("ok"):
        logging.getLogger(__name__).error(
            "doubao-crawl-cli failed type=%s err=%s",
            result.get("error_type"),
            str(result.get("error") or "")[:500],
        )
    _write_result(out_path, result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
