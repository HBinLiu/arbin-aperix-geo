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

定时采样调度（另开终端，与 Worker 同时运行；仅在每日窗口内 tick）：

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
| Celery Beat | 可选 | 每日窗口内扫描到期 subject 并入队 |

`.env` 至少配置 `DATABASE_URL`、`CELERY_BROKER_URL` 与一个采样平台 Key（如 `DOUBAO_API_KEY`）。

**手动触发（本地）：**

```bash
export PYTHONPATH=src
python3 scripts/sampling_trigger.py          # 对最新 subject 触发
python3 scripts/sampling_reparse.py --dry-run  # 重算已有回复的 parsed 字段
```

其它入口：Setup finalize 自动创建 job；本地脚本 `scripts/sampling_trigger.py`；前端 `POST /subjects/{id}/sampling-jobs/retry` 重试失败任务。

每日定时采样在 **北京时间 02:00–05:00** 内按 subject id hash 错开 slot；Beat 仅在该时段内每 `SAMPLING_SCHEDULER_INTERVAL_MINUTES`（默认 15）分钟扫描一次。

## 网页爬取（Crawl4AI）

统一入口：`services/crawl/page.py` 的 `fetch_page()`（httpx 优先，无效时回退 Crawl4AI）。  
元数据提取：`services/crawl/metadata.py` 的 `extract_page_metadata()`（引用页、竞品首页、head 抓取、主体调研共用）。

### 页面元数据提取规则

| 字段 | 来源优先级 |
|------|-----------|
| `title` / `description` | HTML `<head>`（BeautifulSoup，含 `og:title` / `og:description`）→ markdown 首个 `#` 标题或首行 |
| `body_text` / `headings` / `has_table` / `has_code_block` | markdown 正文 ≥ 40 字 **或** HTML 正文不足 40 字 → 用 markdown；否则 `html_to_text` + HTML 标题 |
| favicon | **不在此模块**；仍走 `services/favicon/_parse.py`（只解析 HTML） |

**输入形态：**

- httpx 成功：通常只有 `html`，无 `markdown`
- Crawl4AI 兜底：通常 `html` + `markdown` 并存；正文类字段按上表择优，title/description 仍优先 HTML head

**消费方：**

| 模块 | 用途 |
|------|------|
| `crawl/seo.py` | HTML head / JSON-LD / Microdata 解析与 `SeoProfile` 场景裁剪 |
| `crawl/metadata.py` | 抓取结果 → `PageMetadata`（SEO + 可选正文） |
| `sampling/citation/page.py` | 引用页 `text_snippet`、品牌提及检测 |
| `competitor/web_context.py` | 竞品首页 LLM 画像 |
| `competitor/head_fetch.py` | 竞品候选站 title + 结构化 SEO（`SeoProfile.CROSS_VALIDATE`，`include_body=False`） |
| `setup/llm/payloads.py` | Setup 各 LLM 阶段 user message（含域名 site_data） |
| `crawl/enrich.py` | 资讯 URL SEO enrichment（`SeoProfile.ARTICLE_DISCOVERY`） |

常量：`HEAD_PARSE_MAX_CHARS=120_000`（全量 SEO 解析上限），`PAGE_CRAWL_SEO_MAX_CHARS` 默认 `64_000`（SEO-only 抓取上限），`MIN_BODY_CHARS=40`（与 `PageFetchResult.fetch_ok` 阈值一致）。SEO-only 场景默认不启用 Crawl4AI 兜底（`PAGE_CRAWL_SEO_FALLBACK_ENABLED=false`）。

竞品发现流程（`discover-competitors`，代码在 `services/competitor/`）：

**Onboarding 分步 API（推荐）**

向导 **UI 顺序**：网站/品牌设置 → **选择竞品** → **审查主题** → 确认提示词 → 落库。

| UI | API | 说明 |
|----|-----|------|
| 设置 → 选竞品 | `POST /subjects/setup/discover` | 微观画像 + 竞品发现；body 可带 `session_id` |
| 选竞品 → 审主题 | `POST /subjects/setup/topics` | body: `{ session_id, competitors }`；生成 **profile_summary** + 监测主题 |
| 审主题 → 提示词 | `POST /subjects/setup/prompts` | body: `{ session_id, topics, ... }` |
| 完成 | `POST /subjects/setup/finalize` | body: `{ session_id, competitors, topics }` |

会话默认 24h TTL；竞品搜索后清除 raw crawl；finalize 后删除 session。

**竞品发现 LLM 分工（豆包主路径）**

| 调用 | Prompt / API | 产出 |
|------|--------------|------|
| 2a | 豆包 Responses API（联网） | 竞品 JSON 列表 |
| 2b | `COMPETITOR_CROSS_VALIDATE_SYSTEM` | 候选站 head 抓取 + 交叉验算打分 |
| 2c | `SUBJECT_PROFILE_SUMMARY_SYSTEM` | `profile_summary`（完整 Markdown） |
| 3 | `SETUP_WIZARD_PROMPTS_SYSTEM` | 各 topic 监测问句 |

**域名/品牌模式完整链路**

1. **discover**：域名/品牌爬站 + 微观画像 LLM → 豆包竞品 + 交叉验算（**不含** profile_summary）
2. **topics**：用户确认竞品 → profile_summary LLM + 监测主题 LLM
3. **终选竞品**：及格分 Top N（`COMPETITOR_RESULT_MAX`）

环境变量见 `backend/.env.example`：`COMPETITOR_*`、`DOUBAO_*`；`SEARXNG_BASE_URL` 可选，用于采样后开集品牌域名回填（Setup 竞品发现不用 SearXNG）。安装 Crawl4AI 浏览器（正文类抓取兜底）：

```bash
crawl4ai-setup
# 或：playwright install chromium
```

可调 `PAGE_CRAWL_*` 环境变量，见 `.env.example`。

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

环境、迁移与 API 说明见本文档上文各节。
