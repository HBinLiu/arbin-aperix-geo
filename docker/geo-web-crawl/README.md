# GEO web-crawl（常驻任务服务 + 账号 Chrome 用户目录）

镜像：`aperix/geo-web-crawl:latest`  
用途：采样爬虫 + 登录 probe。豆包会话绑在 **Chromium user-data-dir** 上，与 `geo-crawl-ops` noVNC **共用同一目录**。

```text
VNC 登录（ops Chromium） ──同一 profile──► 心跳 / 采样（geo-web-crawl Chromium）
backend  --HTTP-->  geo-web-crawl:9410  --launch_persistent_context-->  /data/crawl-profiles/<platform>/<account_id>
```

宿主机 `GEO_CRAWL_PROFILE_ROOT`（默认 `/var/lib/aperix/crawl-profiles`）必须同时挂进 crawl 容器、并在 spawn ops 时 `-v` 进去。backend `.env` 里同样要设这个路径。

## 构建 geo-web-crawl

- **Python 3.12**；**精简依赖**（见 `requirements.txt`），不含 redis/celery/openai
- 镜像内安装 Playwright Chromium（与 ops 镜像 `playwright==1.49.1` 对齐）

```bash
mkdir -p /var/lib/aperix/crawl-profiles
docker compose -f docker/geo-web-crawl/docker-compose.yml build --no-cache geo-web-crawl
docker compose -f docker/geo-web-crawl/docker-compose.yml up -d --force-recreate
```

## Compose

见同目录 [`docker-compose.yml`](./docker-compose.yml)。配置用 **`.env`**（从 [`.env.example`](./.env.example) 复制）：

```bash
cd docker/geo-web-crawl
cp -n .env.example .env
docker compose up -d
```

已登录账号第一次切到这套方案时，必须再走一遍 noVNC：旧 Cookie JSON **不能**迁进新 profile。

登录 / 过人机看浏览器：走 `geo-crawl-ops` noVNC 工单，不在 crawl 容器里开可视化。

## 后端配置

```text
GEO_WEB_CRAWL_BASE_URL=http://127.0.0.1:9410
GEO_WEB_CRAWL_TOKEN=change-me
GEO_CRAWL_PROFILE_ROOT=/var/lib/aperix/crawl-profiles
```

## API

- `GET /healthz` → `{ ok, platforms, concurrency, browser_backend }`（`profile` | `local`）
- `POST /v1/jobs`  
  Header: `Authorization: Bearer <GEO_WEB_CRAWL_TOKEN>`  
  Body: `{ "platform": "doubao", "mode": "<mode>", "account_id": "<uuid>", ... }`

设了 `GEO_CRAWL_PROFILE_ROOT` 时必须带 `account_id`（生产）。未设时才允许本机 smoke：`storage_state` + 临时 Chrome。

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

geo-web-crawl：加 replica + 负载均衡；`GEO_WEB_CRAWL_CONCURRENCY` 与账号数对齐（同一 profile 不能双开 Chromium）。

## 本地开发（无 Docker）

```bash
cd backend && PYTHONPATH=src \
  GEO_WEB_CRAWL_CONCURRENCY=1 \
  python -m aperix_geo.services.geo_web_crawl
```

未设 `GEO_CRAWL_PROFILE_ROOT` 时走 ephemeral Chrome + `storage_state`（仅本地 smoke）。
