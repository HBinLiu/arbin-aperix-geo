# Headless GEO web-crawl resident service (platform handlers + HTTP API).
# Prefer pairing with self-hosted Browserless (see docker-compose.yml).
#
# Build from repo root:
#   docker build -t aperix/geo-web-crawl:latest -f docker/geo-web-crawl/Dockerfile .
#
# Backend requires Python >=3.12 (datetime.UTC, etc.) — do not use older Playwright
# jammy images that ship Python 3.10.

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    GEO_WEB_CRAWL_HOST=0.0.0.0 \
    GEO_WEB_CRAWL_PORT=9410 \
    GEO_WEB_CRAWL_CONCURRENCY=2 \
    GEO_WEB_CRAWL_HEADLESS=true

WORKDIR /app

# Minimal OS deps for Playwright driver (CDP/Browserless; no local Chromium).
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      libglib2.0-0 \
      libnss3 \
      libnspr4 \
      libdbus-1-3 \
      libatk1.0-0 \
      libatk-bridge2.0-0 \
      libcups2 \
      libdrm2 \
      libxkbcommon0 \
      libxcomposite1 \
      libxdamage1 \
      libxfixes3 \
      libxrandr2 \
      libgbm1 \
      libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY docker/geo-web-crawl/requirements.txt /app/requirements.txt
# Non-playwright deps: China mirror. playwright from official PyPI (mirrors often 403).
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PIP_TRUSTED_HOST=mirrors.aliyun.com
RUN pip install -i "${PIP_INDEX_URL}" --trusted-host "${PIP_TRUSTED_HOST}" \
      -r /app/requirements.txt \
    && pip install --retries 10 playwright==1.49.1 \
    && python -c "from playwright.sync_api import sync_playwright; print('playwright sync_api ok')"

COPY backend/src /app/src

EXPOSE 9410
WORKDIR /app
CMD ["python", "-m", "aperix_geo.services.geo_web_crawl"]
