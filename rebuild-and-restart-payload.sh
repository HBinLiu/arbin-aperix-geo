#!/usr/bin/env bash
# 拉取代码 →（低内存友好）构建 Payload → 重启或首次创建 aperix-payload
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
SWAPFILE="${APERIX_SWAPFILE:-/swapfile-aperix}"
SWAP_MB="${APERIX_SWAP_MB:-4096}"

mem_kb() { awk '/MemTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0; }
swap_kb() { awk '/SwapTotal:/ {print $2}' /proc/meminfo 2>/dev/null || echo 0; }

ensure_swap() {
  local mem swap need_mb
  mem="$(mem_kb)"
  swap="$(swap_kb)"
  # 物理内存 < 3.5GiB 且几乎无 swap 时补一块，避免 next build OOM SIGKILL
  if [[ "$mem" -ge 3600000 ]]; then
    return 0
  fi
  if [[ "$swap" -ge 2000000 ]]; then
    echo "已有 swap $((swap / 1024)) MiB"
    return 0
  fi
  need_mb="$SWAP_MB"
  echo "物理内存约 $((mem / 1024)) MiB，准备创建 ${need_mb}MiB swap → $SWAPFILE"
  if [[ "$(id -u)" -ne 0 ]]; then
    echo "需要 root 创建 swap；请用 root 执行本脚本，或手动 swapon" >&2
    return 0
  fi
  if [[ ! -f "$SWAPFILE" ]]; then
    dd if=/dev/zero of="$SWAPFILE" bs=1M count="$need_mb" status=progress
    chmod 600 "$SWAPFILE"
    mkswap "$SWAPFILE"
  fi
  swapon "$SWAPFILE" 2>/dev/null || true
  echo "SwapTotal 现为 $(( $(swap_kb) / 1024 )) MiB"
}

# 堆上限不要大于「可用内存」：小机器设 3072 反而更快被 OOM
pick_node_max_old() {
  if [[ -n "${APERIX_NODE_MAX_OLD_SPACE:-}" ]]; then
    echo "$APERIX_NODE_MAX_OLD_SPACE"
    return
  fi
  local mem_mb total_mb
  mem_mb=$(( $(mem_kb) / 1024 ))
  total_mb=$(( mem_mb + $(swap_kb) / 1024 ))
  if [[ "$total_mb" -lt 1800 ]]; then
    echo 1024
  elif [[ "$total_mb" -lt 2800 ]]; then
    echo 1536
  elif [[ "$total_mb" -lt 4500 ]]; then
    echo 2048
  else
    echo 3072
  fi
}

ensure_swap
NODE_MAX_OLD="$(pick_node_max_old)"
echo "NODE max-old-space-size=${NODE_MAX_OLD}（MemTotal=$(( $(mem_kb) / 1024 ))MiB Swap=$(( $(swap_kb) / 1024 ))MiB）"

# 构建期先停掉吃内存的 Node 容器
STOPPED=()
for c in aperix-payload aperix-website; do
  if docker ps --format '{{.Names}}' | grep -qx "$c"; then
    echo "构建前临时 stop $c"
    docker stop "$c"
    STOPPED+=("$c")
  fi
done

cleanup_start() {
  local c
  for c in "${STOPPED[@]+"${STOPPED[@]}"}"; do
    echo "恢复容器 $c"
    docker start "$c" || true
  done
}
trap cleanup_start EXIT

# 有自定义 webpack 时须显式 webpackBuildWorker；并跳过构建期 tsc 降内存
docker run --rm -it --security-opt seccomp:unconfined \
  -v "$ROOT":/repo -w /repo/payload \
  --env-file "$ENV_FILE" \
  -e NODE_OPTIONS="--no-deprecation --max-old-space-size=${NODE_MAX_OLD}" \
  -e NEXT_BUILD_CPUS=1 \
  -e APERIX_LOW_MEM_BUILD=1 \
  node:22-bookworm \
  bash -lc 'npm ci --registry=https://registry.npmmirror.com && npx next build --webpack'

trap - EXIT

# 已有容器则 restart；首次挂载则创建
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

# website 若被停过且不是 payload，上面 restart 只拉了 payload；补 start website
for c in "${STOPPED[@]+"${STOPPED[@]}"}"; do
  if [[ "$c" != "$NAME" ]]; then
    docker start "$c" || true
  fi
done

echo "Payload 已更新并重启"
