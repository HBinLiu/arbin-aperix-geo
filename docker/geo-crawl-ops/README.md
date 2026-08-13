# GEO crawl-ops（多平台共用：豆包 / DeepSeek / 千问…）

镜像：`aperix/geo-crawl-ops:latest`  
用途：爬虫账号运维工单里的远程桌面（登录失效、行为验证码），**不是**采样爬虫 worker。

## 构建

```bash
docker build -t aperix/geo-crawl-ops:latest docker/geo-crawl-ops
```

## 环境变量（API 起容器时注入）

| 变量 | 说明 |
|------|------|
| `GEO_CRAWL_OPS_PLATFORM` | `doubao` / `deepseek` / … |
| `GEO_CRAWL_OPS_START_URL` | 打开的页面 |
| `GEO_CRAWL_OPS_TICKET_TOKEN` | 工单 token |
| `GEO_CRAWL_OPS_TTL_MIN` | 会话软超时（分钟） |
| `GEO_CRAWL_OPS_REASON` | `login_expired`（默认）或 `captcha` |
| `GEO_CRAWL_OPS_STORAGE_STATE_PATH` | 有则 **注入** Playwright Cookie 后再开页 |
| `GEO_CRAWL_OPS_COMPLETE_URL` | 自动关单回调（由 `GEO_CRAWL_OPS_CALLBACK_BASE_URL` 生成） |

容器暴露 **6080**（noVNC）。

### 自动关单

| reason | 条件（连续 2 次轮询） |
|--------|------------------------|
| `login_expired` | 有会话 Cookie，且相对启动基线 **值已变化**（干净浏览器则任意会话 Cookie 即可） |
| `captcha` | 有会话 Cookie，且验证码文案/节点 **已消失**（优先曾见过验证码；否则等 ~20s grace） |

## 后端配置

```text
GEO_CRAWL_OPS_NOVNC_BASE_URL=https://ops-novnc.example
GEO_CRAWL_OPS_DOCKER_IMAGE=aperix/geo-crawl-ops:latest
GEO_CRAWL_OPS_DOCKER_NETWORK=
GEO_CRAWL_OPS_CALLBACK_BASE_URL=http://api:8000
```

`GEO_CRAWL_OPS_NOVNC_BASE_URL` 支持 `{ticket}`、`{port}` 占位。  
同机 Nginx 按端口反代见 [`proxy.nginx.example`](./proxy.nginx.example)，推荐：

```text
GEO_CRAWL_OPS_NOVNC_BASE_URL=https://ops-novnc.example/p/{port}/vnc.html?autoconnect=1&resize=scale&path=p/{port}/websockify
```

起容器的主机需有 `docker` CLI，且当前进程用户能访问 Docker socket。
