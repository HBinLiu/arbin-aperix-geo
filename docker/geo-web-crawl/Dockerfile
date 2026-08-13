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
RUN pip install -r /app/requirements.txt

COPY backend/src /app/src

EXPOSE 9410
WORKDIR /app
CMD ["python", "-m", "aperix_geo.services.geo_web_crawl"]
