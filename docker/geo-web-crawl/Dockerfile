# Headless GEO web-crawl resident service (platform handlers + HTTP API).
# Prefer pairing with self-hosted Browserless (see docker-compose.yml).
#
# Build from repo root:
#   docker build -t aperix/geo-web-crawl:latest -f docker/geo-web-crawl/Dockerfile .
#
# Compose (Browserless + crawl):
#   docker compose -f docker/geo-web-crawl/docker-compose.yml up -d
#
# Backend:
#   GEO_WEB_CRAWL_BASE_URL=http://127.0.0.1:9410
#   GEO_WEB_CRAWL_TOKEN=secret

FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

# Prefer Browserless for Chromium; local launch is only a fallback.
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

COPY docker/geo-web-crawl/requirements.txt /app/requirements.txt
# Non-playwright deps: China mirror (Aliyun). Override with --build-arg if needed.
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PIP_TRUSTED_HOST=mirrors.aliyun.com
# playwright: prefer package already in the Microsoft base image; else official PyPI
# (Tsinghua/some mirrors 403 the manylinux wheel).
RUN pip install -i "${PIP_INDEX_URL}" --trusted-host "${PIP_TRUSTED_HOST}" \
      -r /app/requirements.txt \
    && (python -c "import playwright; print('playwright', playwright.__version__)" \
        || pip install --retries 10 playwright==1.49.1) \
    && python -c "import playwright; print('playwright ok', playwright.__version__)"

COPY backend/src /app/src

EXPOSE 9410
WORKDIR /app
CMD ["python", "-m", "aperix_geo.services.geo_web_crawl"]
