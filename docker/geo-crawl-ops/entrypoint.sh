#!/usr/bin/env bash
# geo-crawl-ops entrypoint: Xvfb + Chromium (Playwright) + x11vnc + noVNC + watcher.
set -euo pipefail

PLATFORM="${GEO_CRAWL_OPS_PLATFORM:-web}"
START_URL="${GEO_CRAWL_OPS_START_URL:-https://www.doubao.com/chat/}"
TICKET="${GEO_CRAWL_OPS_TICKET_TOKEN:-}"
TTL_MIN="${GEO_CRAWL_OPS_TTL_MIN:-15}"
STATE_PATH="${GEO_CRAWL_OPS_STORAGE_STATE_PATH:-}"
REASON="${GEO_CRAWL_OPS_REASON:-login_expired}"
CDP_PORT="${GEO_CRAWL_OPS_CDP_PORT:-9222}"
DONE_FLAG=/tmp/ops-done

echo "[geo-crawl-ops] platform=${PLATFORM} reason=${REASON} ticket=${TICKET:0:8}… start=${START_URL} ttl=${TTL_MIN}m"

Xvfb :1 -screen 0 1440x900x24 -ac +extension GLX +render -noreset &
sleep 1

x11vnc -display :1 -forever -shared -rfbport 5900 -nopw -listen 0.0.0.0 >/tmp/x11vnc.log 2>&1 &
websockify --web=/usr/share/novnc 6080 localhost:5900 >/tmp/websockify.log 2>&1 &

if [[ -n "${STATE_PATH}" && -f "${STATE_PATH}" ]]; then
  echo "[geo-crawl-ops] login baseline from ${STATE_PATH}"
fi

export GEO_CRAWL_OPS_CDP_URL="http://127.0.0.1:${CDP_PORT}"
python3 /usr/local/bin/geo-crawl-ops-launch-browser.py >/tmp/launch_browser.log 2>&1 &
# Give Chromium a moment before watcher attaches.
sleep 4
python3 /usr/local/bin/geo-crawl-ops-watch-login.py >/tmp/watch_login.log 2>&1 &

deadline=$(( $(date +%s) + TTL_MIN * 60 + 60 ))
while (( $(date +%s) < deadline )); do
  if [[ -f "${DONE_FLAG}" ]]; then
    echo "[geo-crawl-ops] ops complete; exiting"
    exit 0
  fi
  sleep 5
done

echo "[geo-crawl-ops] ttl elapsed; exiting"
