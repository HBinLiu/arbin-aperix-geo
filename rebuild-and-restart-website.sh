#!/usr/bin/env bash
# 拉取代码 → 容器内 rebuild 官网 → 重启或首次创建 aperix-website
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

NAME=aperix-website
ENV_FILE="$ROOT/website/.env.production"

# 1. git pull master
git reset --hard HEAD
git pull origin master

# 2. node docker rebuild
docker run --rm -it --security-opt seccomp:unconfined \
  -v "$ROOT":/repo -w /repo/website \
  --env-file "$ENV_FILE" \
  node:22-bookworm \
  bash -lc 'npm ci --registry=https://registry.npmmirror.com && npm run build'

# 3. 已有容器则重启；首次挂载则创建
if docker ps -a --format '{{.Names}}' | grep -qx "$NAME"; then
  echo "容器 $NAME 已存在，执行 restart"
  docker restart "$NAME"
else
  echo "首次挂载：创建容器 $NAME"
  docker run -d --name "$NAME" --restart unless-stopped \
    --security-opt seccomp:unconfined \
    -p 127.0.0.1:4321:4321 \
    -v "$ROOT/website":/app \
    -v "$ROOT/shared":/shared \
    -w /app \
    --env-file "$ENV_FILE" \
    -e HOST=0.0.0.0 \
    -e PORT=4321 \
    node:22-bookworm \
    node ./dist/server/entry.mjs
fi
