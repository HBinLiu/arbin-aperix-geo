#!/usr/bin/env bash
# 在运行中的 crawl 容器里安装与 google-chrome 同版本的 chromedriver（无需 Selenium Manager 联网）。
set -euo pipefail

if ! command -v google-chrome-stable >/dev/null 2>&1; then
  echo "google-chrome-stable not found" >&2
  exit 1
fi

VER="$(google-chrome-stable --product-version)"
URL="https://storage.googleapis.com/chrome-for-testing-public/${VER}/linux64/chromedriver-linux64.zip"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends unzip wget ca-certificates

echo "downloading chromedriver for chrome ${VER} ..."
wget -q "$URL" -O /tmp/chromedriver-linux64.zip
unzip -qo /tmp/chromedriver-linux64.zip -d /tmp/cd
install -m 0755 /tmp/cd/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
rm -rf /tmp/cd /tmp/chromedriver-linux64.zip

echo "ok: /usr/local/bin/chromedriver ($(chromedriver --version 2>/dev/null || true))"
