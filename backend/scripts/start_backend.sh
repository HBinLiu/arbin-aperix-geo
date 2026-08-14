#!/usr/bin/env bash
# 一条命令启动 API + Celery Worker + Beat（开发 / 单机部署均可；Ctrl+C 全部退出）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=src

WITH_BEAT=1
WITH_RELOAD=0
LOGLEVEL="${CELERY_LOGLEVEL:-INFO}"
# 1=分池（默认）；0=单 worker 消费全部队列（本地轻量调试；容量模型变弱）
CELERY_SPLIT_WORKERS="${CELERY_SPLIT_WORKERS:-1}"

usage() {
  cat <<'EOF'
Usage: bash scripts/start_backend.sh [options]

  同时启动 uvicorn、Celery worker，以及（默认）Celery beat。
  默认 CELERY_SPLIT_WORKERS=1：orch / api / crawl / page / parse 五个 worker。
    api   = HTTP 提供商采样（原 llm）
    crawl = 账号池浏览器采样（prefetch=1）
    page  = 引用页抓取（原 crawl 语义）
  Beat 仅在每日采样窗口内（默认北京时间 02:00–05:00）按间隔扫描到期 subject。

  分机部署：本机只起 API+Beat，另用 scripts/start_celery_worker.sh
  并设 CELERY_WORKER_ROLE=orch|api|llm|crawl|page|parse。

Options:
  --no-beat         不启动 Beat（仅 API + Worker）
  --reload          API 启用 uvicorn --reload（仅本地改代码时用）
  --unified-worker  单 worker 消费全部队列（等同 CELERY_SPLIT_WORKERS=0）
  --loglevel LVL    Celery 日志级别（默认 INFO）
  -h, --help        显示帮助
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-beat) WITH_BEAT=0; shift ;;
    --reload) WITH_RELOAD=1; shift ;;
    --unified-worker) CELERY_SPLIT_WORKERS=0; shift ;;
    --loglevel) LOGLEVEL="${2:?missing level}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"
ORCH_CONCURRENCY="${CELERY_ORCH_WORKER_CONCURRENCY:-4}"
API_CONCURRENCY="${CELERY_API_WORKER_CONCURRENCY:-${CELERY_LLM_WORKER_CONCURRENCY:-16}}"
PARSE_CONCURRENCY="${CELERY_PARSE_WORKER_CONCURRENCY:-16}"
UNIFIED_CONCURRENCY="${CELERY_WORKER_CONCURRENCY:-8}"

eval "$(python3 - <<'PY'
from aperix_geo.config import get_settings
s = get_settings()
print(f'DEFAULT_CRAWL_CONCURRENCY={s.celery_crawl_worker_concurrency}')
print(f'DEFAULT_PAGE_CONCURRENCY={s.celery_page_worker_concurrency}')
print(f'DEFAULT_PAGE_MAX_TASKS={s.celery_page_max_tasks_per_child}')
print(f'DEFAULT_PAGE_MAX_MEMORY_KB={s.celery_page_max_memory_per_child_kb}')
PY
)"
CRAWL_CONCURRENCY="${CELERY_CRAWL_WORKER_CONCURRENCY:-$DEFAULT_CRAWL_CONCURRENCY}"
PAGE_CONCURRENCY="${CELERY_PAGE_WORKER_CONCURRENCY:-$DEFAULT_PAGE_CONCURRENCY}"
PAGE_MAX_TASKS_PER_CHILD="${CELERY_PAGE_MAX_TASKS_PER_CHILD:-${CELERY_CRAWL_MAX_TASKS_PER_CHILD:-$DEFAULT_PAGE_MAX_TASKS}}"
PAGE_MAX_MEMORY_PER_CHILD="${CELERY_PAGE_MAX_MEMORY_PER_CHILD:-${CELERY_CRAWL_MAX_MEMORY_PER_CHILD:-$DEFAULT_PAGE_MAX_MEMORY_KB}}"

ALL_QUEUES="$(python3 - <<'PY'
from aperix_geo.celery_queues import celery_worker_queues_for_role
print(celery_worker_queues_for_role("all"))
PY
)"
ORCH_QUEUE="$(python3 - <<'PY'
from aperix_geo.celery_queues import celery_worker_queues_for_role
print(celery_worker_queues_for_role("orch"))
PY
)"
API_QUEUE="$(python3 - <<'PY'
from aperix_geo.celery_queues import celery_worker_queues_for_role
print(celery_worker_queues_for_role("api"))
PY
)"
CRAWL_QUEUE="$(python3 - <<'PY'
from aperix_geo.celery_queues import celery_worker_queues_for_role
print(celery_worker_queues_for_role("crawl"))
PY
)"
PAGE_QUEUE="$(python3 - <<'PY'
from aperix_geo.celery_queues import celery_worker_queues_for_role
print(celery_worker_queues_for_role("page"))
PY
)"
PARSE_QUEUE="$(python3 - <<'PY'
from aperix_geo.celery_queues import celery_worker_queues_for_role
print(celery_worker_queues_for_role("parse"))
PY
)"

PIDS=()
cleanup() {
  echo ""
  echo "Stopping backend processes..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

UVICORN_ARGS=(aperix_geo.main:app --host "$API_HOST" --port "$API_PORT")
if [[ "$WITH_RELOAD" -eq 1 ]]; then
  UVICORN_ARGS+=(--reload)
fi

echo "Starting API (uvicorn) on ${API_HOST}:${API_PORT}..."
uvicorn "${UVICORN_ARGS[@]}" &
PIDS+=($!)

start_worker() {
  local role="$1"
  local queues="$2"
  local concurrency="$3"
  shift 3
  echo "Starting Celery worker role=$role queues=$queues concurrency=$concurrency $*..."
  env CELERY_WORKER_ROLE="$role" \
    celery -A aperix_geo.celery_app.celery_app worker \
    --loglevel="$LOGLEVEL" \
    -Q "$queues" \
    --concurrency="$concurrency" \
    "$@" &
  PIDS+=($!)
}

if [[ "$CELERY_SPLIT_WORKERS" == "1" ]]; then
  start_worker orch "$ORCH_QUEUE" "$ORCH_CONCURRENCY"
  start_worker api "$API_QUEUE" "$API_CONCURRENCY"
  # Account-pool crawl: prefetch=1 so broker holds the real queue.
  start_worker crawl "$CRAWL_QUEUE" "$CRAWL_CONCURRENCY" --prefetch-multiplier=1
  start_worker page "$PAGE_QUEUE" "$PAGE_CONCURRENCY" \
    --max-tasks-per-child="$PAGE_MAX_TASKS_PER_CHILD" \
    --max-memory-per-child="$PAGE_MAX_MEMORY_PER_CHILD"
  start_worker parse "$PARSE_QUEUE" "$PARSE_CONCURRENCY"
else
  echo "WARNING: unified worker weakens crawl capacity isolation; prefer CELERY_SPLIT_WORKERS=1 in production." >&2
  start_worker all "$ALL_QUEUES" "$UNIFIED_CONCURRENCY" \
    --prefetch-multiplier=1 \
    --max-tasks-per-child="$PAGE_MAX_TASKS_PER_CHILD" \
    --max-memory-per-child="$PAGE_MAX_MEMORY_PER_CHILD"
fi
if [[ "$WITH_BEAT" -eq 1 ]]; then
  echo "Starting Celery beat (sampling window only)..."
  celery -A aperix_geo.celery_app.celery_app beat --loglevel="$LOGLEVEL" &
  PIDS+=($!)
fi

echo ""
echo "Backend stack running. Ctrl+C to stop all."
echo "  API:    http://127.0.0.1:${API_PORT}/docs"
if [[ "$CELERY_SPLIT_WORKERS" == "1" ]]; then
  echo "  Workers: orch($ORCH_CONCURRENCY) + api($API_CONCURRENCY) + crawl($CRAWL_CONCURRENCY) + page($PAGE_CONCURRENCY) + parse($PARSE_CONCURRENCY)"
else
  echo "  Worker: unified ($UNIFIED_CONCURRENCY) on $ALL_QUEUES"
fi
if [[ "$WITH_BEAT" -eq 1 ]]; then
  echo "  Beat:   scheduled sampling (02:00–05:00 CST by default)"
fi
echo ""

wait
