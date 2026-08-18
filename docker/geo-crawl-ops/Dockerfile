# Multi-platform crawl remote desktop (Doubao / DeepSeek / Qianwen / …).
# Build: docker build -t aperix/geo-crawl-ops:latest docker/geo-crawl-ops
#
# Runtime contract (set by API when spawning a ticket session):
#   GEO_CRAWL_OPS_PLATFORM          e.g. doubao | deepseek | qianwen
#   GEO_CRAWL_OPS_START_URL         page to open (chat / login)
#   GEO_CRAWL_OPS_TICKET_TOKEN      ticket token (for logging / callback)
#   GEO_CRAWL_OPS_TTL_MIN           soft hint for session lifetime
#   GEO_CRAWL_OPS_STORAGE_STATE_PATH  optional Playwright storage_state.json (injected)
#   GEO_CRAWL_OPS_COMPLETE_URL      optional POST endpoint for auto-complete
#   GEO_CRAWL_OPS_REASON            login_expired | captcha (complete heuristics)
#
# Expose noVNC on 6080. Reverse-proxy GEO_CRAWL_OPS_NOVNC_BASE_URL by ticket
# (see proxy.Caddyfile.example).

FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:1 \
    VNC_PORT=5900 \
    NOVNC_PORT=6080 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    chromium \
    fonts-noto-cjk \
    novnc \
    procps \
    python3 \
    python3-pip \
    websockify \
    x11vnc \
    xauth \
    xvfb \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --break-system-packages playwright==1.49.1 \
    && python3 -m playwright install chromium \
    && python3 -c "from playwright.sync_api import sync_playwright; print('playwright ok')"

COPY entrypoint.sh /usr/local/bin/geo-crawl-ops-entrypoint.sh
COPY launch_browser.py /usr/local/bin/geo-crawl-ops-launch-browser.py
COPY watch_login.py /usr/local/bin/geo-crawl-ops-watch-login.py
RUN chmod +x /usr/local/bin/geo-crawl-ops-entrypoint.sh \
    && chmod +x /usr/local/bin/geo-crawl-ops-launch-browser.py \
    && chmod +x /usr/local/bin/geo-crawl-ops-watch-login.py

EXPOSE 6080
WORKDIR /data
ENTRYPOINT ["/usr/local/bin/geo-crawl-ops-entrypoint.sh"]
