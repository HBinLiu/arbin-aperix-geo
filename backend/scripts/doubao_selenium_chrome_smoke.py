#!/usr/bin/env python3
"""A/B smoke: Selenium + Google Chrome + 白名单 HTTP 代理，打开豆包看验证码/风控文案.

仅诊断。不写 cookie、不灌号、不进生产采样队列。
生产仍走 geo-web-crawl（Playwright）。若这里同样「换个网络 / 图片加载失败」，问题在出口 IP，不是驱动。

宿主机与 crawl 容器应共用同一公网 IP（青果白名单）。不要在笔记本上测生产代理。

有桌面:
  sudo apt-get install -y google-chrome-stable
  cd backend && .venv/bin/pip install 'selenium>=4.8'
  set -a && source ../docker/geo-web-crawl/.env && set +a
  PYTHONPATH=src .venv/bin/python scripts/doubao_selenium_chrome_smoke.py

生产 SSH（无桌面）:
  PYTHONPATH=src .venv/bin/python scripts/doubao_selenium_chrome_smoke.py \\
    --headless --screenshot /tmp/doubao-chrome.png --wait-s 12
  PYTHONPATH=src .venv/bin/python scripts/doubao_selenium_chrome_smoke.py --ip-only --headless
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aperix_geo.services.providers.doubao_web.selectors import CHAT_URL  # noqa: E402

_CHROME_CANDIDATES = (
    "google-chrome-stable",
    "google-chrome",
    "chromium",
    "chromium-browser",
)

_RISK_HINTS = (
    "换个网络",
    "图片加载失败",
    "行为验证",
    "验证码",
    "网络异常",
)


def _proxy_url() -> str:
    return (
        os.environ.get("HTTPS_PROXY")
        or os.environ.get("HTTP_PROXY")
        or os.environ.get("https_proxy")
        or os.environ.get("http_proxy")
        or ""
    ).strip()


def _chrome_bin(explicit: str) -> str:
    raw = (explicit or os.environ.get("GEO_WEB_CRAWL_CHROME_BIN") or "").strip()
    if raw:
        path = Path(raw)
        if path.is_file():
            return str(path)
        raise SystemExit(f"chrome binary not found: {raw}")
    for name in _CHROME_CANDIDATES:
        found = shutil.which(name)
        if found:
            return found
    raise SystemExit(
        "install Google Chrome (google-chrome-stable) or set GEO_WEB_CRAWL_CHROME_BIN"
    )


def _proxy_server_arg(raw: str) -> str:
    parsed = urlparse(raw if "://" in raw else f"http://{raw}")
    host = parsed.hostname
    if not host:
        raise SystemExit(f"invalid proxy URL: {raw}")
    scheme = (parsed.scheme or "http").lower()
    port = parsed.port or (1080 if scheme.startswith("socks") else 8080)
    if parsed.username or parsed.password:
        print(
            "whitelist mode should not include user:pass in the proxy URL",
            file=sys.stderr,
        )
    if scheme in {"socks5", "socks5h"}:
        return f"socks5://{host}:{port}"
    if scheme == "socks4":
        return f"socks4://{host}:{port}"
    return f"http://{host}:{port}"


def _scan_risk_text(text: str) -> list[str]:
    lower = text or ""
    return [hint for hint in _RISK_HINTS if hint in lower]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=CHAT_URL)
    parser.add_argument("--chrome-bin", default="")
    parser.add_argument(
        "--proxy",
        default="",
        help="override HTTP_PROXY (whitelist: http://ip:port or ip:port, no user/pass)",
    )
    parser.add_argument(
        "--ip-url",
        default="http://myip.ipip.net",
        help="exit-IP check page (Qingguo sample uses myip.ipip.net)",
    )
    parser.add_argument(
        "--ip-only",
        action="store_true",
        help="only print exit IP page_source, do not open Doubao",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Chrome headless (for production SSH without desktop)",
    )
    parser.add_argument(
        "--screenshot",
        default="",
        help="save Doubao page PNG (recommended with --headless)",
    )
    parser.add_argument(
        "--wait-s",
        type=float,
        default=8.0,
        help="seconds to wait after opening Doubao before screenshot/scan",
    )
    parser.add_argument(
        "--no-pause",
        action="store_true",
        help="do not wait for Enter (implied by --headless)",
    )
    parser.add_argument("--chromedriver", default="", help="optional chromedriver path")
    args = parser.parse_args()

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        print("pip install 'selenium>=4.8'", file=sys.stderr)
        return 1

    chrome = _chrome_bin(args.chrome_bin)
    proxy_raw = (args.proxy or _proxy_url()).strip()
    options = Options()
    options.binary_location = chrome
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-quic")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--disable-gpu")
    if args.headless:
        options.add_argument("--headless=new")
    if proxy_raw:
        server = _proxy_server_arg(proxy_raw)
        options.add_argument(f"--proxy-server={server}")
        options.add_argument("--force-webrtc-ip-handling-policy=disable_non_proxied_udp")
        options.add_argument("--disable-ipv6")
        print(f"proxy={server} (whitelist, no auth header)")
    else:
        print("WARNING: no HTTP_PROXY; Doubao will see this machine's IP", file=sys.stderr)

    print(f"chrome={chrome} headless={args.headless}")
    service = Service(args.chromedriver) if args.chromedriver.strip() else Service()
    driver = webdriver.Chrome(service=service, options=options)
    try:
        caps = driver.capabilities or {}
        print(f"browserName={caps.get('browserName')} version={caps.get('browserVersion')}")
        print(f"exit-ip check {args.ip_url}")
        driver.get(args.ip_url)
        body = driver.page_source or ""
        print("--- page_source ---")
        print(body)
        print("--- end ---")
        if args.ip_only:
            return 0

        print(f"open {args.url}")
        driver.get(args.url)
        time.sleep(max(0.0, float(args.wait_s)))

        try:
            visible = driver.execute_script(
                "return (document.body && (document.body.innerText || '')) || ''"
            ) or ""
        except Exception:
            visible = ""
        hits = _scan_risk_text(visible) or _scan_risk_text(driver.page_source or "")
        if hits:
            print(f"RISK_HINTS: {', '.join(hits)}")
            snippet = visible.strip().replace("\n", " ")[:800]
            if snippet:
                print(f"body_snip: {snippet}")
        else:
            print("RISK_HINTS: (none matched in body text)")

        shot = (args.screenshot or "").strip()
        if shot:
            path = Path(shot)
            path.parent.mkdir(parents=True, exist_ok=True)
            driver.save_screenshot(str(path))
            print(f"screenshot={path.resolve()}")

        if not args.headless and not args.no_pause:
            print("看验证码图能否出来，然后回车结束（不保存登录态）")
            input()
    finally:
        driver.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
