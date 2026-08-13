"""CLI entry for geo-web-crawl Playwright jobs (Docker / host subprocess).

Modes:
  crawl — full chat sample (default)
  probe — login heartbeat

Uses Sync Playwright in an isolated process (geo-web-crawl image has modern glibc).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any


def _fail(message: str, *, error_type: str = "CrawlError") -> dict[str, Any]:
    return {
        "ok": False,
        "error_type": error_type,
        "error": message,
        "human_ops": False,
        "storage_state": None,
    }


def _write_result(out_path: Path, result: dict[str, Any]) -> None:
    out_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="GEO web Playwright job (crawl|probe)")
    parser.add_argument("--in", dest="in_path", required=True, help="Input JSON payload path")
    parser.add_argument("--out", dest="out_path", required=True, help="Output JSON result path")
    parser.add_argument(
        "--mode",
        choices=("crawl", "probe"),
        default="crawl",
        help="crawl=sampling chat; probe=login heartbeat",
    )
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

    mode = str(payload.get("mode") or args.mode or "crawl").strip().lower()
    if mode not in ("crawl", "probe"):
        mode = "crawl"

    from aperix_geo.services.geo_web_crawl.cli_runtime import run_geo_web_cli_job

    logging.getLogger(__name__).info("geo-web-crawl-cli: mode=%s sync_playwright", mode)
    result = run_geo_web_cli_job(payload, mode=mode)
    if not result.get("ok"):
        logging.getLogger(__name__).error(
            "geo-web-crawl-cli failed mode=%s type=%s err=%s",
            mode,
            result.get("error_type"),
            str(result.get("error") or "")[:500],
        )
    _write_result(out_path, result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
