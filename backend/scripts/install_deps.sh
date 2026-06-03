#!/usr/bin/env bash
# 安装 backend 依赖。若遇 SSLCertVerificationError，会自动用 --trusted-host 并重试（仅建议本机开发）。
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TH=(--trusted-host pypi.org --trusted-host files.pythonhosted.org)

if python3 -m pip install -e '.[dev]' 2>/dev/null; then
  echo "OK: pip install -e '.[dev]'"
  exit 0
fi

echo "常规 pip 安装失败（常见原因：SSL 证书链不完整）。正在使用 --trusted-host + --no-build-isolation 重试…" >&2
python3 -m pip install -U pip setuptools wheel "${TH[@]}"
python3 -m pip install --no-build-isolation -e '.[dev]' "${TH[@]}"
echo "OK: 已通过备用方式安装依赖。"
