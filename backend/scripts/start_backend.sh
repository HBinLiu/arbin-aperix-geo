#!/usr/bin/env bash
# 一条命令启动 API + Celery Worker + Beat（开发 / 单机部署均可；Ctrl+C 全部退出）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH=src

WITH_BEAT=1
WITH_RELOAD=0
LOGLEVEL="${CELERY_LOGLEVEL:-INFO}"
WORKER_CONCURRENCY="${CELERY_WORKER_CONCURRENCY:-}"

usage() {
  cat <<'EOF'
Usage: bash scripts/start_backend.sh [options]

  同时启动 uvicorn、Celery worker，以及（默认）Celery beat。
  读取环境变量 API_HOST、API_PORT（或 .env）；Celery 使用 CELERY_BROKER_URL 等。

Options:
  --no-beat       不启动 Beat（仅 API + Worker）
  --reload        API 启用 uvicorn --reload（仅本地改代码时用）
  --loglevel LVL  Celery 日志级别（默认 INFO）
  -h, --help      显示帮助
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-beat) WITH_BEAT=0; shift ;;
    --reload) WITH_RELOAD=1; shift ;;
    --loglevel) LOGLEVEL="${2:?missing level}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"

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

WORKER_ARGS=(-A aperix_geo.celery_app.celery_app worker --loglevel="$LOGLEVEL")
if [[ -n "$WORKER_CONCURRENCY" ]]; then
  WORKER_ARGS+=(--concurrency="$WORKER_CONCURRENCY")
fi

echo "Starting Celery worker..."
celery "${WORKER_ARGS[@]}" &
PIDS+=($!)

if [[ "$WITH_BEAT" -eq 1 ]]; then
  echo "Starting Celery beat..."
  celery -A aperix_geo.celery_app.celery_app beat --loglevel="$LOGLEVEL" &
  PIDS+=($!)
fi

echo ""
echo "Backend stack running. Ctrl+C to stop all."
echo "  API:    http://127.0.0.1:${API_PORT}/docs"
echo "  Worker: sampling execution"
if [[ "$WITH_BEAT" -eq 1 ]]; then
  echo "  Beat:   scheduled sampling tick"
fi
echo ""

wait
