# GEO web-crawl（常驻任务服务 + Browserless 浏览器）

镜像：`aperix/geo-web-crawl:latest`  
用途：采样爬虫 + 登录 probe（豆包已接；DeepSeek / 千问 handler 占位）。  
与 `geo-crawl-ops`（人工 noVNC）分离。

**推荐生产形态**：`geo-web-crawl` 只跑任务 API / 平台 handler；**Chromium 交给自建 Browserless**。

```text
backend  --HTTP-->  geo-web-crawl:9410  --WS-->  browserless:3000
```

## 构建 geo-web-crawl

```bash
docker build -t aperix/geo-web-crawl:latest -f docker/geo-web-crawl/Dockerfile .
```

## Compose（Browserless + crawl）

见同目录 [`docker-compose.yml`](./docker-compose.yml)：

```bash
cd docker/geo-web-crawl && docker compose up -d
```

手动等价：

```bash
# 1) Browserless（浏览器池）
docker run -d --restart=unless-stopped --name browserless \
  --shm-size=2g -p 3000:3000 \
  -e TOKEN=change-me \
  -e HOST=0.0.0.0 \
  -e CONCURRENT=4 \
  -e QUEUED=8 \
  -e TIMEOUT=600000 \
  ghcr.io/browserless/chromium

# 2) geo-web-crawl（业务；连 Browserless）
docker run -d --restart=unless-stopped --name geo-web-crawl \
  -p 9410:9410 \
  -e GEO_WEB_CRAWL_CONCURRENCY=2 \
  -e GEO_WEB_CRAWL_TOKEN=change-me \
  -e GEO_WEB_CRAWL_BROWSER_WS_URL=ws://browserless:3000/chromium/playwright \
  -e GEO_WEB_CRAWL_BROWSERLESS_TOKEN=change-me \
  --link browserless:browserless \
  aperix/geo-web-crawl:latest
```

> Browserless 默认 `TIMEOUT=30000`（30s）太短，采样请调到 ≥ crawl 超时（上例 10 分钟），或 `-1`（务必保证任务结束会 `browser.close()`）。  
> 跨容器访问必须 `HOST=0.0.0.0`。

### 连接 URL

| 模式 | URL | Playwright API |
|------|-----|----------------|
| **推荐** Playwright native | `ws://browserless:3000/chromium/playwright?token=…` | `chromium.connect` |
| CDP | `ws://browserless:3000?token=…` 或 `/chromium` | `chromium.connect_over_cdp` |

未设 `GEO_WEB_CRAWL_BROWSER_WS_URL` 时，服务回退为**进程内 `chromium.launch()`**（开发 / 无 Browserless）。

## 后端配置

```text
GEO_WEB_CRAWL_BASE_URL=http://127.0.0.1:9410
GEO_WEB_CRAWL_TOKEN=change-me
GEO_WEB_CRAWL_TIMEOUT_S=180
```

Browserless 相关变量配在 **crawl 容器**（不是 Celery），见 compose。

## API

- `GET /healthz` → `{ ok, platforms, concurrency, browser_backend }`（`browserless` | `local`）
- `POST /v1/jobs`  
  Header: `Authorization: Bearer <GEO_WEB_CRAWL_TOKEN>`  
  Body: `{ "platform": "doubao", "mode": "crawl"|"probe", "storage_state": {...}, ... }`

## 扩展平台

在 `aperix_geo/services/geo_web_crawl/handlers/` 新增模块并 `register_platform`。  
`deepseek` / `qianwen` 已 stub。

## 扩容

- Browserless：提高 `CONCURRENT` / 加 replica  
- geo-web-crawl：加 replica + 负载均衡；`GEO_WEB_CRAWL_CONCURRENCY` ≤ Browserless 可用槽位

## 本地开发（无 Docker 浏览器）

```bash
cd backend && PYTHONPATH=src \
  GEO_WEB_CRAWL_CONCURRENCY=2 \
  python -m aperix_geo.services.geo_web_crawl
```

或本机 Browserless +：

```bash
GEO_WEB_CRAWL_BROWSER_WS_URL=ws://127.0.0.1:3000/chromium/playwright \
GEO_WEB_CRAWL_BROWSERLESS_TOKEN=change-me \
python -m aperix_geo.services.geo_web_crawl
```
