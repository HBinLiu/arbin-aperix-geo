# GEO web-crawl（常驻任务服务 + Browserless 浏览器）

镜像：`aperix/geo-web-crawl:latest`  
用途：采样爬虫 + 登录 probe（豆包已接；DeepSeek / 千问 handler 占位）。  
与 `geo-crawl-ops`（人工 noVNC）分离。

**推荐生产形态**：`geo-web-crawl` 只跑任务 API / 平台 handler；**Chromium 交给自建 Browserless**。

```text
backend  --HTTP-->  geo-web-crawl:9410  --WS-->  browserless:3000
```

## 构建 geo-web-crawl

- **Python 3.12**；**精简依赖**（见 `requirements.txt`），不含 redis/celery/openai
- 构建时会跑 import 检查：crawl 启动路径若再拉取重依赖会直接失败
- Chromium 由 Browserless 提供

```bash
docker compose -f docker/geo-web-crawl/docker-compose.yml build --no-cache geo-web-crawl
docker compose -f docker/geo-web-crawl/docker-compose.yml up -d --force-recreate
```

## Compose（Browserless + crawl）

见同目录 [`docker-compose.yml`](./docker-compose.yml)。配置用 **`.env`**（从 [`.env.example`](./.env.example) 复制；compose 自动加载）：

```bash
cd docker/geo-web-crawl
cp -n .env.example .env   # 已有 .env 则跳过
# 按需改 TOKEN / LIVE_VIEW 等
docker compose up -d
```

Browserless 映射宿主机 **`3001→3000`**（避开常见的 3000 占用），供 Debugger / liveURL；crawl 容器内仍用 `ws://browserless:3000/chromium`。

### 实时看浏览器（调试）

编辑 `.env`：

```text
GEO_WEB_CRAWL_LIVE_VIEW=1
GEO_WEB_CRAWL_LIVE_VIEW_PAUSE_S=25
GEO_WEB_CRAWL_LIVE_VIEW_SCREENSHOT_DIR=/tmp/geo-crawl-live
GEO_WEB_CRAWL_LIVE_VIEW_BASE_URL=http://127.0.0.1:3001
```

然后：

```bash
docker compose up -d --force-recreate
# 若改过 crawl 代码需先: docker compose build geo-web-crawl
```

触发一次豆包采样（或 curl `POST /v1/jobs`）后：

| 看什么 | 怎么看 |
|--------|--------|
| liveURL | `docker compose logs -f geo-web-crawl` 搜 `LIVE VIEW (open in browser)`（需镜像支持 Hybrid；开源版可能没有） |
| Browserless UI | `http://127.0.0.1:3001/`（TOKEN 与 `.env` 一致；远程请用 SSH 隧道） |
| 截图回放 | `docker/geo-web-crawl/live-shots/frame-*.png` |

关掉：`.env` 改回 `LIVE_VIEW=0`、`PAUSE_S=0`、清空 `SCREENSHOT_DIR`，再 `up -d --force-recreate`。

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
  -e GEO_WEB_CRAWL_BROWSER_WS_URL=ws://browserless:3000/chromium \
  -e GEO_WEB_CRAWL_BROWSERLESS_TOKEN=change-me \
  --link browserless:browserless \
  aperix/geo-web-crawl:latest
```

> Browserless 默认 `TIMEOUT=30000`（30s）太短，采样请调到 ≥ crawl 超时（上例 10 分钟），或 `-1`（务必保证任务结束会 `browser.close()`）。  
> 跨容器访问必须 `HOST=0.0.0.0`。

### 连接 URL

| 模式 | URL | Playwright API | 说明 |
|------|-----|----------------|------|
| **推荐 CDP** | `ws://browserless:3000/chromium?token=…` | `chromium.connect_over_cdp` | 版本宽松，生产默认 |
| Playwright native | `ws://browserless:3000/chromium/playwright?token=…` | `chromium.connect` | **必须**与 Browserless 内置 Playwright 同版本，否则易 `KeyError: selectors` |

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
  Body: `{ "platform": "doubao", "mode": "<mode>", "storage_state": {...}, ... }`

豆包 `mode`：

| mode | 作用 |
|------|------|
| `crawl` | 整页 UI：对话 → 扇出 → `share_url`（默认） |
| `probe` | 登录心跳；默认轻量发短会话检行为验证码（不等全文），结束后删除该会话 |
| `sign` | 页内 `frontierSign` → `a_bogus` / fingerprint |
| `http` | 页内 `fetch` 打 samantha completion（正文/扇出；无 share） |
| `share` | 短 UI：打开会话只取 `share_url` |

Hybrid 采样（backend）：`DOUBAO_WEB_HTTP_ENABLED=true` + `DOUBAO_CRAWL_TRANSPORT=hybrid` → `http` + `share`。默认仍为 `ui`（整页 `crawl`）。仅借鉴协议/签名思路，**不**提供 OpenAI 兼容网关。

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
