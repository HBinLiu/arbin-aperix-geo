# GEO web-crawl（常驻任务服务 + 账号 Chrome 用户目录 + noVNC）

镜像：`aperix/geo-web-crawl:latest`  
用途：采样爬虫、登录 probe、**登录工单桌面**。豆包会话绑在 **Chromium user-data-dir** 上；心跳 / 采样 / 运维登录共用这一份。

```text
backend  --HTTP :9410-->  geo-web-crawl（compose 常驻，不是工单时 docker run）
                              ├── POST /v1/jobs
                              ├── POST /v1/login-sessions  → 已有容器里开 headed Chrome
                              └── noVNC 默认 :6080
profile: /data/crawl-profiles/<platform>/<account_id>
```

宿主机 `GEO_CRAWL_PROFILE_ROOT`（默认 `/var/lib/aperix/crawl-profiles`）必须同时挂进 crawl 容器，并与 backend `.env` 相同。

## 构建

```bash
mkdir -p /var/lib/aperix/crawl-profiles
docker compose -f docker/geo-web-crawl/docker-compose.yml build --no-cache geo-web-crawl
docker compose -f docker/geo-web-crawl/docker-compose.yml up -d --force-recreate
```

headed 登录用镜像里的 Debian `/usr/bin/chromium`（不要 Playwright 自带 Chrome + SwiftShader）。

出网代理写在 `docker/geo-web-crawl/.env`（`HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY`）。代理在宿主机上时用 `http://host.docker.internal:<port>`，不要写 `127.0.0.1`（那是容器自己）。`NO_PROXY` 须含 `host.docker.internal`，否则关单回调也会走代理。SOCKS5 必须写成 `socks5://host:port`（写成 `http://` 时 Chromium 仍走 HTTP CONNECT，豆包会闪验证码再提示换网络）。改代理协议后需 **rebuild** crawl 镜像（WebRTC/IPv6 泄漏修复在镜像源码里）；只改 `.env` 地址则 `up -d --force-recreate` 即可。

## Compose

见同目录 [`docker-compose.yml`](./docker-compose.yml)。配置用 **`.env`**（从 [`.env.example`](./.env.example) 复制）：

```bash
cd docker/geo-web-crawl
cp -n .env.example .env
docker compose up -d
```

| 端口 | 用途 |
|------|------|
| 9410 | 任务 / 登录会话 HTTP |
| 6080 | noVNC（compose 默认；工单 `{port}` 用实例上报的 `vnc_port`，不必在 `.env` 填） |

反代见 [`proxy.nginx.example`](./proxy.nginx.example)。backend：

```text
GEO_WEB_CRAWL_BASE_URL=http://127.0.0.1:9410
GEO_WEB_CRAWL_TOKEN=change-me
GEO_CRAWL_PROFILE_ROOT=/var/lib/aperix/crawl-profiles
GEO_CRAWL_OPS_NOVNC_BASE_URL=https://ops-novnc.example/p/{port}/vnc.html?autoconnect=1&resize=scale&path=p/{port}/websockify
GEO_CRAWL_OPS_CALLBACK_BASE_URL=https://app.aperix.cn
```

`{port}` 来自该实例 `healthz` / `login-sessions` 的 `vnc_port`（默认 6080）。不要在 crawl `.env` 里手填端口。以后若按号自动拉起容器，由 Docker 分配宿主机端口再回写 `vnc_port`。

已登录账号第一次切到这套方案时，必须再走一遍 noVNC：旧 Cookie JSON **不能**迁进新 profile。

多账号仍可待在**一个** crawl 容器里（并发 ≤ 账号数）。可视化是同一块 Xvfb：并行时窗口会叠在一起。号变多再按号拆容器（自动分配宿主机端口，而不是在 `.env` 写死）。

## API

- `GET /healthz` → `{ ok, platforms, concurrency, browser_backend, vnc, vnc_port }`
- `POST /v1/jobs`  
  Header: `Authorization: Bearer <GEO_WEB_CRAWL_TOKEN>`  
  Body: `{ "platform": "doubao", "mode": "<mode>", "account_id": "<uuid>", ... }`
- `POST /v1/login-sessions` — 开工单桌面（backend 调用，不要人手打）
- `GET /v1/login-sessions/{account_id}` — 工单 Chromium 是否还在
- `POST /v1/login-sessions/stop` — 关登录 Chrome，**不**停 VNC / 容器

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

## 扩容

`GEO_WEB_CRAWL_CONCURRENCY` 与账号数对齐（同一 profile 不能双开 Chromium）。加 replica 时每个 replica 不要挂同一份 profile。

## 本地开发（无 Docker）

```bash
cd backend && PYTHONPATH=src \
  GEO_WEB_CRAWL_CONCURRENCY=1 \
  python -m aperix_geo.services.crawl_browser
```

未设 `GEO_CRAWL_PROFILE_ROOT` 时走 ephemeral Chrome + `storage_state`（仅本地 smoke）。无 Xvfb 时保持 `GEO_WEB_CRAWL_VNC=false`（默认无头）。
