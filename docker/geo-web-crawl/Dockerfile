# Headless GEO web-crawl resident service (platform handlers + HTTP API).
# Prefer pairing with self-hosted Browserless (see docker-compose.yml).
#
# Build from repo root:
#   docker build -t aperix/geo-web-crawl:latest -f docker/geo-web-crawl/Dockerfile .
#
# Python >=3.12. Lean deps only — crawl import graph must stay free of
# redis/celery/openai (enforced by build-time import check).

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
COPY backend/src /app/src

ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG PIP_TRUSTED_HOST=mirrors.aliyun.com
RUN pip install -i "${PIP_INDEX_URL}" --trusted-host "${PIP_TRUSTED_HOST}" \
      -r /app/requirements.txt \
    && pip install --retries 15 playwright==1.49.1 \
    && python - <<'PY'
"""Fail the image build if crawl startup imports heavy backend deps."""
import sys

class Block:
    BAD = {"redis", "celery", "openai", "crawl4ai", "dashscope", "psycopg", "alembic", "sqlalchemy"}

    def find_spec(self, fullname, path, target=None):
        root = fullname.split(".", 1)[0]
        if root in self.BAD:
            raise ImportError(f"geo-web-crawl must not import {root!r} at startup")
        return None

sys.meta_path.insert(0, Block())
from datetime import UTC  # noqa: F401
from playwright.sync_api import sync_playwright  # noqa: F401
from aperix_geo.services.geo_web_crawl.registry import ensure_handlers_loaded
from aperix_geo.services.providers.doubao_web.jobs import crawl as _crawl_job  # noqa: F401
from aperix_geo.services.providers.doubao_web.jobs import probe as _probe_job  # noqa: F401
from aperix_geo.services.providers.doubao_web import crawler as _crawler  # noqa: F401

ensure_handlers_loaded()
print("geo-web-crawl lean import check ok")
PY

EXPOSE 9410
WORKDIR /app
CMD ["python", "-m", "aperix_geo.services.geo_web_crawl"]
