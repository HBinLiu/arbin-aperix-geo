# Aperix AI — 后端（API + Worker）

Python 单体：**FastAPI**、**Celery**、**PostgreSQL**、**Redis**。与前端通过 HTTP 隔离，仅暴露 REST/OpenAPI。

## 目录

| 路径 | 说明 |
|------|------|
| `src/aperix_geo/` | 应用代码 |
| `alembic/` | 数据库迁移 |
| `alembic.ini` | Alembic 配置 |
| `pyproject.toml` | 依赖与打包 |
| `.env.example` | 环境变量模板（复制为 `.env`） |

## 本地运行（在 `backend/` 下执行）

```bash
# 仓库根目录已起 Docker 时（Postgres + Redis）
cd backend
python3 -m venv .venv && source .venv/bin/activate   # 或在仓库根建 .venv 后 pip install -e './backend[dev]'
pip install -e '.[dev]'
# 若出现 SSL: CERTIFICATE_VERIFY_FAILED（常见于 macOS 自带 Python.org 安装包未跑证书脚本），任选其一：
#   1) 运行一次：/Applications/Python\ 3.12/Install\ Certificates.command（版本号与 python3 一致）
#   2) 在 backend/ 执行：bash scripts/install_deps.sh
cp .env.example .env   # 编辑 DATABASE_URL、REDIS_*、CELERY_*、DEEPSEEK_*、JWT_SECRET_KEY 等
export PYTHONPATH=src
python -m alembic upgrade head
```

**一条命令启动 API + Worker + Beat：**

```bash
export PYTHONPATH=src
bash scripts/start_backend.sh
# 本地改代码热重载：bash scripts/start_backend.sh --reload
# 不要定时采样：bash scripts/start_backend.sh --no-beat
```

或分别开终端：

```bash
# 使用 .env 中的 API_HOST / API_PORT（默认 0.0.0.0:8000）：
python -m aperix_geo
# 开发热重载：uvicorn aperix_geo.main:app --reload --host 0.0.0.0 --port 8000
```

Worker（另开终端，同样在 `backend/` 且已 `activate`）：

```bash
export PYTHONPATH=src
celery -A aperix_geo.celery_app.celery_app worker --loglevel=INFO
```

定时采样调度（另开终端，与 Worker 同时运行）：

```bash
export PYTHONPATH=src
celery -A aperix_geo.celery_app.celery_app beat --loglevel=INFO
```

OpenAPI：`http://localhost:8000/docs`

## 采样

API 只**创建**采样任务；真正调用 LLM 的是 **Celery Worker**。仅开 uvicorn 时 job 会停在 `queued`。

| 组件 | 必须 | 作用 |
|------|------|------|
| PostgreSQL + Redis | ✅ | 数据与队列 |
| Celery Worker | ✅ | 执行采样 |
| API | 按需 | 前端 / HTTP 触发 |
| Celery Beat | 可选 | 按品牌页间隔自动采样 |

`.env` 至少配置 `DATABASE_URL`、`CELERY_BROKER_URL` 与一个采样平台 Key（如 `DOUBAO_API_KEY`）。

**手动触发（本地）：**

```bash
export PYTHONPATH=src
python3 scripts/sampling_trigger.py          # 对最新 subject 触发
python3 scripts/sampling_reparse.py --dry-run  # 重算已有回复的 parsed 字段
```

其它入口：Setup 完成自动创建 job；`POST /api/v1/subjects/{id}/sampling-jobs`（需 JWT）；开发调试入口见 `.env.example` 中 `SAMPLING_DEBUG_*`。

Beat 按 `SAMPLING_SCHEDULER_TICK_SECONDS`（默认 15 分钟）扫描到期主体；品牌页可配间隔（6h / 12h / 每天 / 3 天 / 每周 / 关闭）。

更完整联调步骤见 [../docs/07-后端联调.md](../docs/07-后端联调.md#采样)。

## 网页爬取（Crawl4AI）

竞品发现流程（`discover-competitors`，代码在 `services/competitor/`）：

**Onboarding 分步 API（推荐）**

1. `POST /subjects/discover-profile` — 监测站首页 → 微观利基画像，返回 `session_id` + `micro_keywords`（Redis 缓存 1h）
2. 用户审查/编辑主题（keywords）
3. `POST /subjects/discover-competitors` — body: `{ session_id, micro_keywords?, profile? }`，基于确认后的画像搜索竞品

**域名模式完整链路**

1. **首页抓取**：默认 httpx 轻量取 title/description；失败时回退 Crawl4AI
2. **微观利基画像**：LLM → `industry`、`core_features`、`target_customers`、`micro_keywords`
3. **SearXNG**：多轮 query（`SEARXNG_BASE_URL` 必填）；预排除媒体/聚合站
4. **交叉验算**：轻量抓取竞品候选站元数据 + LLM 对标打分（0–10），高分不足时按分数顺延
5. **终选**：按分数取 Top，或 LLM 从高分候选中挑最多 5 个主域名
6. **输出**：可打开校验 + 中文站点名 → `{ domains, competitors: [{domain, site_name}] }`

环境变量见 `backend/.env.example`：**大模型**按厂商分块；**竞品发现**为 `COMPETITOR_*` 与 `SEARXNG_BASE_URL`（抓取超时、结果数量等见 `services/competitor/defaults.py` 映射）。须配 `SEARXNG_BASE_URL`。安装 Crawl4AI 浏览器（只需一次）：

```bash
crawl4ai-setup
# 或：playwright install chromium
```

可调 `WEB_CRAWL_*` 环境变量，见 `.env.example`。

## 阿里云短信（可选）

`POST /api/v1/auth/send-code` 在 **`ENV` 为 `development` / `dev` / `local`（默认）** 且 `channel=phone` 时，**不调用短信网关**，生成随机验证码写入 Redis，并在响应字段 **`dev_code`** 中回显。生产请设置 **`ENV=production`**；此时若 `SMS_ALIYUN_ENABLED=true` 则调用阿里云 **SendSms**（依赖 `alibabacloud-dysmsapi20170525`）。变量见 `backend/.env.example`：`SMS_ALIYUN_ACCESS_KEY_*`、`SMS_ALIYUN_SIGN_NAME`、`SMS_ALIYUN_TEMPLATE_CODE` 等；模板内验证码变量名须与 `SMS_ALIYUN_TEMPLATE_PARAM_CODE_KEY` 一致。发送失败时接口返回 **503**。开发环境下邮箱/手机验证码均在 **`dev_code`** 回显；邮箱通道生产仍为占位（日志）。

## 从仓库根目录安装（可选）

不进入 `backend/` 也可安装可编辑包（便于单一虚拟环境）：

```bash
pip install -e './backend[dev]'
```

迁移与 Alembic **仍建议在 `backend/` 目录执行**（以便读取同目录下的 `alembic.ini` 与 `.env`）：

```bash
cd backend && export PYTHONPATH=src && python -m alembic upgrade head
```

## 与前端约定

- API 前缀：`/api/v1`
- 认证：`Authorization: Bearer <access_token>`，或开发用 `X-API-Key`（见 `.env.example`）

更完整的验收步骤见 [../docs/07-后端联调.md](../docs/07-后端联调.md)。
