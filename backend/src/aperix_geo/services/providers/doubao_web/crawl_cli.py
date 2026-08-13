"""CLI entry for Doubao browser crawl in a fresh OS process (not Celery daemon child)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


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
        out_path.write_text(
            json.dumps(
                {
                    "ok": False,
                    "error_type": "DoubaoCrawlError",
                    "error": f"invalid input payload: {exc}",
                    "human_ops": False,
                    "storage_state": None,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return 2

    from aperix_geo.services.providers.doubao_web.browser_crawl_job import (
        run_doubao_browser_crawl_job,
    )

    result = run_doubao_browser_crawl_job(payload if isinstance(payload, dict) else {})
    out_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
