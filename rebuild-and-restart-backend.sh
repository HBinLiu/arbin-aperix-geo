#!/usr/bin/env bash
# 拉取代码 → 确保 Python>=3.12 → venv 安装依赖 → alembic → 安装/重启 aperix-backend.service
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

BACKEND="$ROOT/backend"
UNIT_NAME=aperix-backend.service
UNIT_DST="${APERIX_SYSTEMD_DIR:-/etc/systemd/system}/$UNIT_NAME"
VENV="$BACKEND/.venv"
VENV_BIN="$VENV/bin"
# 可选覆盖：APERIX_PYTHON=/usr/local/bin/python3.12
PYTHON_BIN=""

run_root() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

python_ok() {
  local bin="$1"
  command -v "$bin" >/dev/null 2>&1 || [[ -x "$bin" ]] || return 1
  "$bin" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null
}

resolve_python() {
  local c
  if [[ -n "${APERIX_PYTHON:-}" ]]; then
    if python_ok "$APERIX_PYTHON"; then
      PYTHON_BIN="$APERIX_PYTHON"
      return 0
    fi
    echo "APERIX_PYTHON=$APERIX_PYTHON 不可用或版本 < 3.12" >&2
  fi
  for c in python3.13 python3.12 python3; do
    if command -v "$c" >/dev/null 2>&1 && python_ok "$c"; then
      PYTHON_BIN="$(command -v "$c")"
      return 0
    fi
  done
  return 1
}

install_python_via_pkg() {
  echo "尝试用系统包管理器安装 Python >= 3.12 ..."
  if command -v apt-get >/dev/null 2>&1; then
    run_root apt-get update -y
    run_root DEBIAN_FRONTEND=noninteractive apt-get install -y \
      python3.12 python3.12-venv python3.12-dev || return 1
    return 0
  fi
  if command -v dnf >/dev/null 2>&1; then
    run_root dnf install -y python3.12 python3.12-devel 2>/dev/null \
      || run_root dnf install -y python3.12 || return 1
    return 0
  fi
  # CentOS/RHEL 7 的 yum 通常没有 3.12，交给 uv
  return 1
}

install_python_via_uv() {
  echo "系统包无 Python 3.12（常见于 CentOS 7），改用 uv 安装独立解释器（不覆盖系统 python）..."
  export PATH="${HOME}/.local/bin:/usr/local/bin:${PATH}"
  if ! command -v uv >/dev/null 2>&1; then
    if ! command -v curl >/dev/null 2>&1; then
      echo "需要 curl 以安装 uv" >&2
      return 1
    fi
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="${HOME}/.local/bin:${PATH}"
  fi
  if ! command -v uv >/dev/null 2>&1; then
    echo "uv 安装失败" >&2
    return 1
  fi
  uv python install 3.12
  PYTHON_BIN="$(uv python find 3.12)"
  if ! python_ok "$PYTHON_BIN"; then
    echo "uv 安装的 Python 不可用: $PYTHON_BIN" >&2
    return 1
  fi
}

ensure_python() {
  if resolve_python; then
    return 0
  fi
  echo "当前无可用 Python >= 3.12（系统 python3: $(python3 --version 2>&1 || echo 未安装)），开始自动安装..."
  if install_python_via_pkg && resolve_python; then
    return 0
  fi
  if install_python_via_uv; then
    return 0
  fi
  echo "自动安装 Python 3.12 失败。可手动指定：APERIX_PYTHON=/path/to/python3.12 $0" >&2
  exit 1
}

# --- 1. 前置检查 ---
if ! command -v systemctl >/dev/null 2>&1; then
  echo "未找到 systemctl，本脚本仅支持 systemd 主机" >&2
  exit 1
fi

ensure_python

if [[ ! -f "$BACKEND/.env.production" ]]; then
  echo "缺少 $BACKEND/.env.production（从 backend/.env.example 复制并填写，勿提交密钥）" >&2
  exit 1
fi

SERVICE_USER="${APERIX_SERVICE_USER:-${SUDO_USER:-$(id -un)}}"
SERVICE_GROUP="${APERIX_SERVICE_GROUP:-$(id -gn "$SERVICE_USER" 2>/dev/null || id -gn)}"

echo "Python: $("$PYTHON_BIN" --version) ($PYTHON_BIN)  ServiceUser: $SERVICE_USER"

# --- 2. venv + 依赖 ---
if [[ ! -x "$VENV_BIN/python" ]]; then
  echo "创建虚拟环境 $VENV"
  "$PYTHON_BIN" -m venv "$VENV"
fi

if ! "$VENV_BIN/python" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then
  echo "venv Python 过旧，用 $PYTHON_BIN 重建..."
  rm -rf "$VENV"
  "$PYTHON_BIN" -m venv "$VENV"
fi

echo "安装 backend 依赖..."
"$VENV_BIN/pip" install -U pip setuptools wheel

# CentOS 7 等自带 GCC 4.8，编不了现代 numpy（meson/cython）。强制走 wheel，禁止源码编译这些包。
gcc_major="$(gcc -dumpversion 2>/dev/null | cut -d. -f1 || echo 0)"
if [[ "${gcc_major:-0}" -lt 9 ]]; then
  echo "检测到 GCC ${gcc_major}（过旧），pip 对原生扩展仅使用二进制 wheel（不本地编译）"
  export PIP_PREFER_BINARY=1
  export PIP_ONLY_BINARY="numpy,scipy,pandas,pillow,cryptography,lxml,pydantic-core,aiohttp,yarl,multidict,frozenlist,greenlet,rpds-py,jiter,numexpr,kiwisolver,contourpy,pyarrow"
fi

if ! "$VENV_BIN/pip" install -e "$BACKEND"; then
  echo "依赖安装失败。GCC 过旧时请确保能从 PyPI 拉取 manylinux wheel；或安装新编译器后重试：" >&2
  echo "  yum install -y centos-release-scl && yum install -y devtoolset-11-gcc devtoolset-11-gcc-c++" >&2
  echo "  scl enable devtoolset-11 -- ./rebuild-and-restart-backend.sh" >&2
  exit 1
fi

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
