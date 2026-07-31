#!/usr/bin/env bash
# 拉取代码 → 容器内 rebuild Payload → 重启或首次创建 aperix-payload
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

NAME=aperix-payload
ENV_FILE="$ROOT/payload/.env.production"
# 低内存机（常见 1～2G）next build 易被 OOM SIGKILL；可用 APERIX_NODE_MAX_OLD_SPACE 覆盖
NODE_MAX_OLD="${APERIX_NODE_MAX_OLD_SPACE:-3072}"

# node docker rebuild（限制 webpack 并发 + 提高堆上限；勿用 npm run build 里的 cross-env 覆盖 NODE_OPTIONS）
docker run --rm -it --security-opt seccomp:unconfined \
  -v "$ROOT":/repo -w /repo/payload \
  --env-file "$ENV_FILE" \
  -e NODE_OPTIONS="--no-deprecation --max-old-space-size=${NODE_MAX_OLD}" \
  -e NEXT_BUILD_CPUS=1 \
  node:22-bookworm \
  bash -lc 'npm ci --registry=https://registry.npmmirror.com && npx next build --webpack'

# 已有容器则重启；首次挂载则创建
if docker ps -a --format '{{.Names}}' | grep -qx "$NAME"; then
  echo "容器 $NAME 已存在，执行 restart"
  docker restart "$NAME"
else
  echo "首次挂载：创建容器 $NAME"
  docker run -d --name "$NAME" --restart unless-stopped \
    --security-opt seccomp:unconfined \
    -p 127.0.0.1:3000:3000 \
    -v "$ROOT/payload":/app \
    -v "$ROOT/shared":/shared \
    -w /app \
    --env-file "$ENV_FILE" \
    -e HOSTNAME=0.0.0.0 \
    -e PORT=3000 \
    node:22-bookworm \
    npm start
fi
