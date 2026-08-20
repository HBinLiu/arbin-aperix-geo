#!/usr/bin/env bash
# geo-web-crawl: optional Xvfb + fluxbox + noVNC, then the HTTP job server.
set -euo pipefail

VNC_RAW="${GEO_WEB_CRAWL_VNC:-false}"
VNC_ON=0
case "${VNC_RAW,,}" in
  1|true|yes|on) VNC_ON=1 ;;
esac

if [[ "${VNC_ON}" -eq 1 ]]; then
  export DISPLAY="${DISPLAY:-:1}"
  export GEO_WEB_CRAWL_HEADLESS="${GEO_WEB_CRAWL_HEADLESS:-false}"
  if [[ "${GEO_WEB_CRAWL_HEADLESS,,}" =~ ^(1|true|yes|on)$ ]]; then
    echo "[geo-web-crawl] GEO_WEB_CRAWL_VNC=true forces headed Chromium" >&2
    export GEO_WEB_CRAWL_HEADLESS=false
  fi

  NOVNC_LISTEN="${GEO_WEB_CRAWL_NOVNC_PORT:-6080}"
  NOVNC_PUBLIC="${GEO_WEB_CRAWL_NOVNC_PUBLIC_PORT:-$NOVNC_LISTEN}"
  echo "[geo-web-crawl] desktop display=${DISPLAY} novnc_listen=${NOVNC_LISTEN} novnc_public=${NOVNC_PUBLIC}"

  Xvfb :1 -screen 0 1440x900x24 -ac +extension GLX +render -noreset >/tmp/xvfb.log 2>&1 &
  for _ in $(seq 1 40); do
    if xdpyinfo -display :1 >/dev/null 2>&1; then
      break
    fi
    sleep 0.25
  done
  if ! xdpyinfo -display :1 >/dev/null 2>&1; then
    echo "[geo-web-crawl] Xvfb failed to start" >&2
    cat /tmp/xvfb.log >&2 || true
    exit 1
  fi

  xsetroot -display :1 -solid "#2d2d2d" >/dev/null 2>&1 || true
  fluxbox >/tmp/fluxbox.log 2>&1 &
  sleep 0.4

  # Chrome under Xvfb: avoid xdamage-driven full-window flashes when the compositor paints.
  x11vnc -display :1 -forever -shared -rfbport 5900 -nopw -listen 0.0.0.0 \
    -noxdamage -wait 10 -defer 10 \
    >/tmp/x11vnc.log 2>&1 &
  websockify --web=/usr/share/novnc "${NOVNC_LISTEN}" localhost:5900 >/tmp/websockify.log 2>&1 &
fi

exec python -m aperix_geo.services.crawl_browser
