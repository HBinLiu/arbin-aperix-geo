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

Cookie 来源：优先读 launch 进程写入的 `/tmp/ops-live-storage-state.json`（CDP `storage_state` 在本镜像里常为 0 cookies，不可靠）。

登录浏览器使用 **Playwright persistent user-data-dir**（`GEO_CRAWL_OPS_PROFILE_DIR`，与 geo-web-crawl 共用宿主机目录）。不要再把另一台 Chrome 的 Cookie JSON 灌进来。

黑屏：VNC 已连上但 Chromium 没画出来。常见原因是上次 `docker rm -f` 留下 `SingletonLock`。镜像会清锁、起 fluxbox。headed 登录仍用 **Debian `/usr/bin/chromium`**（重构前能输入的那套），不要用 Playwright 自带 Chrome + SwiftShader（输入即崩）。

输入时容器消失：旧 watcher 把游客页的 `uid_tt` 当成已登录 → `complete-by-token` → `docker rm --rm`。现需 `sessionid`/`sid_guard` 且页面上没有「登录」才关单。

```bash
docker build -t aperix/geo-crawl-ops:latest docker/geo-crawl-ops
docker logs "$(docker ps -qf label=aperix.geo_crawl_ops=1)" --tail 80
docker exec "$(docker ps -qf label=aperix.geo_crawl_ops=1)" cat /tmp/launch_browser.log
docker exec "$(docker ps -qf label=aperix.geo_crawl_ops=1)" cat /tmp/watch_login.log
```

## 后端配置

```text
GEO_CRAWL_OPS_NOVNC_BASE_URL=https://ops-novnc.example
GEO_CRAWL_OPS_DOCKER_IMAGE=aperix/geo-crawl-ops:latest
GEO_CRAWL_OPS_CALLBACK_BASE_URL=https://app.aperix.cn
GEO_CRAWL_PROFILE_ROOT=/var/lib/aperix/crawl-profiles
```

生产 API 若只绑 `127.0.0.1`，不要用 `172.17.0.1:8000`；走公网/反代根地址（不要加 `/api` 后缀）。
`GEO_CRAWL_OPS_NOVNC_BASE_URL` 支持 `{ticket}`、`{port}` 占位。  
同机 Nginx 按端口反代见 [`proxy.nginx.example`](./proxy.nginx.example)，推荐：

```text
GEO_CRAWL_OPS_NOVNC_BASE_URL=https://ops-novnc.example/p/{port}/vnc.html?autoconnect=1&resize=scale&path=p/{port}/websockify
```

起容器的主机需有 `docker` CLI，且当前进程用户能访问 Docker socket。
