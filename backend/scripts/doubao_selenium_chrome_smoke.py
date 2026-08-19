#!/usr/bin/env python3
"""A/B smoke: Selenium + Chrome/Chromium + 白名单 HTTP 代理，打开豆包看验证码/风控文案.

仅诊断。不写 cookie、不灌号、不进生产采样队列。
生产仍走 geo-web-crawl（Playwright）。若这里同样「换个网络 / 图片加载失败」，问题在出口 IP，不是驱动。

推荐：在 crawl 容器里跑（Xvfb + noVNC 可视化）::

  docker compose exec geo-web-crawl /app/scripts/smoke-doubao.sh --browser chrome
  docker compose exec geo-web-crawl /app/scripts/smoke-doubao.sh --browser chromium

宿主机（有桌面）::

  cd backend && .venv/bin/pip install 'selenium>=4.8'
  set -a && source ../docker/geo-web-crawl/.env && set +a
  PYTHONPATH=src .venv/bin/python scripts/doubao_selenium_chrome_smoke.py

宿主机无桌面::

  PYTHONPATH=src .venv/bin/python scripts/doubao_selenium_chrome_smoke.py \\
    --headless --screenshot /tmp/doubao-chrome.png --wait-s 12
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
_SRC = ROOT / "src"
if _SRC.is_dir():
    sys.path.insert(0, str(_SRC))

from aperix_geo.services.providers.doubao_web.selectors import CHAT_URL  # noqa: E402
from aperix_geo.services.crawl_accounts.ticket_urls import build_novnc_desktop_url  # noqa: E402

_CHROME_ONLY = (
    "google-chrome-stable",
    "google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/google-chrome",
)
_CHROMIUM_ONLY = ("chromium", "chromium-browser", "/usr/bin/chromium")
_CHROMEDRIVER_CHROMIUM = ("/usr/bin/chromedriver", "/usr/lib/chromium/chromedriver")
_CHROMEDRIVER_CHROME = ("/usr/local/bin/chromedriver",)
_ALL_BROWSERS = _CHROME_ONLY + _CHROMIUM_ONLY

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


def _resolve_binary(candidates: tuple[str, ...], *, use_crawl_default: bool = True) -> str:
    if use_crawl_default:
        explicit = (os.environ.get("GEO_WEB_CRAWL_CHROME_BIN") or "").strip()
        if explicit and Path(explicit).is_file():
            return explicit
    for name in candidates:
        if name.startswith("/"):
            if Path(name).is_file():
                return name
            continue
        found = shutil.which(name)
        if found:
            return found
    raise SystemExit(f"browser binary not found; tried {candidates}")


def _chrome_bin(explicit: str, browser: str) -> str:
    if explicit.strip():
        path = Path(explicit.strip())
        if path.is_file():
            return str(path)
        raise SystemExit(f"chrome binary not found: {explicit}")
    if browser == "chrome":
        return _resolve_binary(_CHROME_ONLY, use_crawl_default=False)
    if browser == "chromium":
        return _resolve_binary(_CHROMIUM_ONLY, use_crawl_default=False)
    return _resolve_binary(_ALL_BROWSERS, use_crawl_default=True)


def _is_chromium_binary(browser_bin: str) -> bool:
    name = Path(browser_bin).name
    return name in {"chromium", "chromium-browser"} or browser_bin.endswith("/chromium")


def _chromedriver_service(explicit: str, browser_bin: str) -> object:
    from selenium.webdriver.chrome.service import Service

    if explicit.strip():
        path = explicit.strip()
        if not Path(path).is_file():
            raise SystemExit(f"chromedriver not found: {path}")
        print(f"chromedriver={path}", flush=True)
        return Service(path)

    candidates = _CHROMEDRIVER_CHROMIUM if _is_chromium_binary(browser_bin) else _CHROMEDRIVER_CHROME
    for path in candidates:
        if Path(path).is_file():
            print(f"chromedriver={path}", flush=True)
            return Service(path)

    hint = (
        "/usr/bin/chromedriver（apt chromium-driver）"
        if _is_chromium_binary(browser_bin)
        else "/usr/local/bin/chromedriver（与 google-chrome 同版本，build 时安装）"
    )
    raise SystemExit(
        f"chromedriver 未找到，需要 {hint}。"
        " 临时修复: docker compose exec geo-web-crawl /app/scripts/install-chromedriver.sh"
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
    return [hint for hint in _RISK_HINTS if hint in (text or "")]


def _novnc_desktop_url() -> str:
    base = (os.environ.get("GEO_CRAWL_OPS_NOVNC_BASE_URL") or "").strip()
    if not base:
        raise SystemExit(
            "GEO_CRAWL_OPS_NOVNC_BASE_URL 未设置（须与 backend .env 相同）"
        )
    try:
        port = int(
            os.environ.get("GEO_WEB_CRAWL_NOVNC_PUBLIC_PORT")
            or os.environ.get("GEO_WEB_CRAWL_NOVNC_PORT")
            or "6080"
        )
    except ValueError:
        port = 6080
    url = build_novnc_desktop_url(base, host_port=port)
    if not url:
        raise SystemExit("GEO_CRAWL_OPS_NOVNC_BASE_URL 无效")
    return url


def _print_novnc_hint() -> None:
    print(f"noVNC: {_novnc_desktop_url()}")


def _apply_common_options(options: object, *, headless: bool) -> None:
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-quic")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--disable-dbus")
    if headless:
        options.add_argument("--disable-gpu")
        options.add_argument("--headless=new")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=CHAT_URL)
    parser.add_argument("--chrome-bin", default="")
    parser.add_argument(
        "--browser",
        choices=("auto", "chrome", "chromium"),
        default="auto",
        help="chrome=Google Chrome; chromium=系统 Chromium（与 crawl Playwright 同系）",
    )
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
        help="headless (default: headed when DISPLAY is set)",
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
    except ImportError:
        print("pip install 'selenium>=4.8'", file=sys.stderr)
        return 1

    headless = args.headless or not (os.environ.get("DISPLAY") or "").strip()
    chrome = _chrome_bin(args.chrome_bin, args.browser)
    proxy_raw = (args.proxy or _proxy_url()).strip()
    options = Options()
    options.binary_location = chrome
    _apply_common_options(options, headless=headless)
    if proxy_raw:
        server = _proxy_server_arg(proxy_raw)
        options.add_argument(f"--proxy-server={server}")
        options.add_argument("--force-webrtc-ip-handling-policy=disable_non_proxied_udp")
        options.add_argument("--disable-ipv6")
        print(f"proxy={server} (whitelist, no auth header)")
    else:
        print("WARNING: no HTTP_PROXY; Doubao will see this machine's IP", file=sys.stderr)

    print(f"browser={chrome} headless={headless} kind={args.browser}", flush=True)
    if not headless:
        _print_novnc_hint()

    print("starting WebDriver…", flush=True)
    service = _chromedriver_service(args.chromedriver, chrome)
    driver = webdriver.Chrome(service=service, options=options)
    print("WebDriver started", flush=True)
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
            if not headless and not args.no_pause:
                print("出口 IP 已显示；回车关闭浏览器")
                input()
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

        if not headless and not args.no_pause:
            print("在 noVNC 里看验证码/风控页；看完后回车结束（不保存登录态）")
            input()
    finally:
        driver.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
