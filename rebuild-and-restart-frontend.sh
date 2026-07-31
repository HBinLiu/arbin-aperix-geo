#!/usr/bin/env bash
# 拉取代码 → 容器内 build 控制台静态产物（frontend/dist）；无需常驻容器
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# --- 0. 先拉代码，再以最新脚本继续 ---
if [[ "${APERIX_REEXEC:-}" != "1" ]]; then
  git reset --hard HEAD
  git pull origin main
  export APERIX_REEXEC=1
  exec bash "$ROOT/$(basename "${BASH_SOURCE[0]}")" "$@"
fi

ENV_FILE="$ROOT/frontend/.env.production"
DIST="$ROOT/frontend/dist"

# 宝塔把站点根指到 dist 时会写入 .user.ini（常带 immutable），Vite emptyOutDir 会报 ENOTDIR
if [[ -e "$DIST/.user.ini" ]]; then
  echo "移除宝塔 $DIST/.user.ini ..."
  chattr -i "$DIST/.user.ini" 2>/dev/null || true
  rm -f "$DIST/.user.ini"
fi

# node docker build → frontend/dist
docker run --rm -it --security-opt seccomp:unconfined \
  -v "$ROOT":/repo -w /repo/frontend \
  --env-file "$ENV_FILE" \
  node:22-bookworm \
  bash -lc 'rm -f dist/.user.ini; npm ci --registry=https://registry.npmmirror.com && npm run build'

echo "构建完成：frontend/dist"
