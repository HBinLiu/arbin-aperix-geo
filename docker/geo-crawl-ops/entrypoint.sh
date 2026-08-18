#!/usr/bin/env bash
# geo-crawl-ops entrypoint: Xvfb + fluxbox + Chromium (Playwright) + x11vnc + noVNC + watcher.
set -euo pipefail

export DISPLAY="${DISPLAY:-:1}"
PLATFORM="${GEO_CRAWL_OPS_PLATFORM:-web}"
START_URL="${GEO_CRAWL_OPS_START_URL:-https://www.doubao.com/chat/}"
TICKET="${GEO_CRAWL_OPS_TICKET_TOKEN:-}"
TTL_MIN="${GEO_CRAWL_OPS_TTL_MIN:-15}"
STATE_PATH="${GEO_CRAWL_OPS_STORAGE_STATE_PATH:-}"
REASON="${GEO_CRAWL_OPS_REASON:-login_expired}"
CDP_PORT="${GEO_CRAWL_OPS_CDP_PORT:-9222}"
DONE_FLAG=/tmp/ops-done

echo "[geo-crawl-ops] platform=${PLATFORM} reason=${REASON} ticket=${TICKET:0:8}… start=${START_URL} ttl=${TTL_MIN}m display=${DISPLAY}"

Xvfb :1 -screen 0 1440x900x24 -ac +extension GLX +render -noreset >/tmp/xvfb.log 2>&1 &
for _ in $(seq 1 20); do
  if xdpyinfo -display :1 >/dev/null 2>&1; then
    break
  fi
  sleep 0.25
done
if ! xdpyinfo -display :1 >/dev/null 2>&1; then
  echo "[geo-crawl-ops] Xvfb failed to start" >&2
  cat /tmp/xvfb.log >&2 || true
  exit 1
fi

xsetroot -display :1 -solid "#2d2d2d" >/dev/null 2>&1 || true
fluxbox >/tmp/fluxbox.log 2>&1 &
sleep 0.5

x11vnc -display :1 -forever -shared -rfbport 5900 -nopw -listen 0.0.0.0 >/tmp/x11vnc.log 2>&1 &
websockify --web=/usr/share/novnc 6080 localhost:5900 >/tmp/websockify.log 2>&1 &

if [[ -n "${STATE_PATH}" && -f "${STATE_PATH}" ]]; then
  echo "[geo-crawl-ops] login baseline from ${STATE_PATH}"
fi

export GEO_CRAWL_OPS_CDP_URL="http://127.0.0.1:${CDP_PORT}"
python3 /usr/local/bin/geo-crawl-ops-launch-browser.py >/tmp/launch_browser.log 2>&1 &
# Give Chromium a moment before watcher attaches.
sleep 4
if ! grep -q "browser ready" /tmp/launch_browser.log 2>/dev/null; then
  echo "[geo-crawl-ops] chromium not ready; launch log:" >&2
  cat /tmp/launch_browser.log >&2 || true
fi
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
