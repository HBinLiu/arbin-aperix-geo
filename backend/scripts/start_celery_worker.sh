#!/usr/bin/env bash
# 启动单个 Celery worker（单机分池或分机部署）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=src

LOGLEVEL="${CELERY_LOGLEVEL:-INFO}"
ROLE="${CELERY_WORKER_ROLE:-all}"

usage() {
  cat <<'EOF'
Usage: bash scripts/start_celery_worker.sh

  消费采样相关 Celery 队列。分机部署时在同一 Redis broker 上起不同 role：

    CELERY_WORKER_ROLE=orch   # 编排：finalize / continue / beat 同类任务
    CELERY_WORKER_ROLE=llm    # 平台 LLM（sampling_llm）
    CELERY_WORKER_ROLE=crawl  # 引用页抓取（sampling_crawl）
    CELERY_WORKER_ROLE=parse  # ABSA + 引用合并（sampling_parse）
    CELERY_WORKER_ROLE=all    # 开发：四队列合一（默认）

  并发（可用环境变量覆盖）：
    CELERY_ORCH_WORKER_CONCURRENCY
    CELERY_LLM_WORKER_CONCURRENCY
    CELERY_CRAWL_WORKER_CONCURRENCY
    CELERY_PARSE_WORKER_CONCURRENCY

  -h, --help  显示帮助
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

QUEUES="$(python3 - <<'PY'
from aperix_geo.celery_queues import celery_worker_queues_for_role
import os
print(celery_worker_queues_for_role(os.environ.get("CELERY_WORKER_ROLE", "all")))
PY
)"

case "$ROLE" in
  orch)
    CONCURRENCY="${CELERY_ORCH_WORKER_CONCURRENCY:-4}"
  ;;
  llm)
    CONCURRENCY="${CELERY_LLM_WORKER_CONCURRENCY:-16}"
  ;;
  crawl)
    CONCURRENCY="${CELERY_CRAWL_WORKER_CONCURRENCY:-16}"
  ;;
  parse)
    CONCURRENCY="${CELERY_PARSE_WORKER_CONCURRENCY:-16}"
  ;;
  all)
    CONCURRENCY="${CELERY_WORKER_CONCURRENCY:-8}"
  ;;
  *)
    echo "Invalid CELERY_WORKER_ROLE=$ROLE (use orch|llm|crawl|parse|all)" >&2
    exit 1
  ;;
esac

export CELERY_WORKER_ROLE="$ROLE"

echo "Starting Celery worker role=$ROLE queues=$QUEUES concurrency=$CONCURRENCY..."
exec celery -A aperix_geo.celery_app.celery_app worker \
  --loglevel="$LOGLEVEL" \
  -Q "$QUEUES" \
  --concurrency="$CONCURRENCY"
