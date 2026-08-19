#!/usr/bin/env bash
# 在 crawl 容器 Xvfb 上开 Selenium 浏览器对照豆包（noVNC 可视化）。
# 不写 cookie、不进采样队列。采样/心跳进行中请勿并行跑。
set -euo pipefail

export DISPLAY="${DISPLAY:-:1}"
export PYTHONPATH="${PYTHONPATH:-/app/src}"

NOVNC_URL="$(
  python - <<'PY'
import os
import sys

from aperix_geo.services.crawl_accounts.ticket_urls import build_novnc_desktop_url

base = (os.environ.get("GEO_CRAWL_OPS_NOVNC_BASE_URL") or "").strip()
if not base:
    print(
        "GEO_CRAWL_OPS_NOVNC_BASE_URL 未设置（须与 backend .env 相同）",
        file=sys.stderr,
    )
    sys.exit(1)
try:
    port = int(
        os.environ.get("GEO_WEB_CRAWL_NOVNC_PUBLIC_PORT")
        or os.environ.get("GEO_WEB_CRAWL_NOVNC_PORT")
        or "6080"
    )
except ValueError:
    port = 6080
url = build_novnc_desktop_url(base, host_port=port)
if not url:
    print("GEO_CRAWL_OPS_NOVNC_BASE_URL 无效", file=sys.stderr)
    sys.exit(1)
print(url)
PY
)"

echo "[smoke] DISPLAY=${DISPLAY}"
echo "[smoke] noVNC（与工单邮件 login_url 同模板）:"
echo "  ${NOVNC_URL}"
echo "[smoke] 先打开上述链接，再跑 smoke；浏览器会出现在虚拟桌面"
echo "[smoke] 用法示例:"
echo "  $0 --browser chrome --ip-only          # 只看出口 IP"
echo "  $0 --browser chrome                    # Google Chrome + 豆包"
echo "  $0 --browser chromium                  # 系统 Chromium（与 Playwright 同系）"
echo

exec python /app/scripts/doubao_selenium_chrome_smoke.py "$@"
