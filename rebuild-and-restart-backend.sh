#!/usr/bin/env bash
# 拉取代码 → 检查 Python → venv 安装依赖 → alembic → 安装/重启 aperix-backend.service
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
UNIT_NAME=aperix-backend.service
UNIT_DST="${APERIX_SYSTEMD_DIR:-/etc/systemd/system}/$UNIT_NAME"
VENV="$BACKEND/.venv"
VENV_BIN="$VENV/bin"

run_root() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

# --- 0. 前置检查 ---
if ! command -v systemctl >/dev/null 2>&1; then
  echo "未找到 systemctl，本脚本仅支持 systemd 主机" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "未找到 python3，请先安装 Python >= 3.12（如 apt install python3.12 python3.12-venv）" >&2
  exit 1
fi

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then
  echo "需要 Python >= 3.12，当前: $(python3 --version 2>&1)" >&2
  exit 1
fi

if [[ ! -f "$BACKEND/.env.production" ]]; then
  echo "缺少 $BACKEND/.env.production" >&2
  exit 1
fi

SERVICE_USER="${APERIX_SERVICE_USER:-${SUDO_USER:-$(id -un)}}"
SERVICE_GROUP="${APERIX_SERVICE_GROUP:-$(id -gn "$SERVICE_USER" 2>/dev/null || id -gn)}"

echo "Python: $(python3 --version)  ServiceUser: $SERVICE_USER"

cd "$ROOT"

# --- 1. git pull ---
git reset --hard HEAD
git pull origin main

# --- 2. venv + 依赖 ---
if [[ ! -x "$VENV_BIN/python" ]]; then
  echo "创建虚拟环境 $VENV"
  python3 -m venv "$VENV"
fi

if ! "$VENV_BIN/python" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then
  echo "venv Python 过旧，重建..."
  rm -rf "$VENV"
  python3 -m venv "$VENV"
fi

echo "安装 backend 依赖..."
"$VENV_BIN/pip" install -U pip
"$VENV_BIN/pip" install -e "$BACKEND"

# --- 3. 迁移 ---
echo "alembic upgrade head..."
(
  cd "$BACKEND"
  export ENV=production
  export PYTHONPATH=src
  "$VENV_BIN/python" -m alembic upgrade head
)

# --- 4. 写入 systemd 单元（ExecStart → start_backend.sh）---
tmp="$(mktemp)"
cat >"$tmp" <<EOF
[Unit]
Description=Aperix GEO backend (API + Celery via start_backend.sh)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${BACKEND}
Environment=ENV=production
Environment=PYTHONPATH=src
Environment=PATH=${VENV_BIN}:/usr/local/bin:/usr/bin
ExecStart=/bin/bash ${BACKEND}/scripts/start_backend.sh
Restart=always
RestartSec=5
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
EOF
run_root cp "$tmp" "$UNIT_DST"
rm -f "$tmp"
run_root systemctl daemon-reload

# --- 5. 已启用/运行中则 restart；否则 enable --now ---
if systemctl is-enabled --quiet "$UNIT_NAME" 2>/dev/null \
  || systemctl is-active --quiet "$UNIT_NAME" 2>/dev/null; then
  echo "单元已存在，执行 restart: $UNIT_NAME"
  run_root systemctl restart "$UNIT_NAME"
else
  echo "首次挂载：enable --now $UNIT_NAME"
  run_root systemctl enable --now "$UNIT_NAME"
fi

echo ""
echo "Backend 已更新并重启"
echo "  状态: systemctl status $UNIT_NAME"
echo "  日志: journalctl -u aperix-backend -f"
echo "  API:  127.0.0.1:8000"
