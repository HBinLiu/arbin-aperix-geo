# arbin-aperix-geo

**Aperix AI** 面向中国大陆市场的 **GEO / AEO** 监测与行动建议产品。本仓库为 **前后端分离的单仓（monorepo）**：后端与前端分目录、分依赖、分进程，通过 **HTTP API** 集成。

## 目录结构

| 目录 | 说明 |
|------|------|
| [**backend/**](backend/) | Python：**FastAPI** + **Celery** + **PostgreSQL** / **Redis**，详见 [backend/README.md](backend/README.md) |
| [**frontend/**](frontend/) | 前端：**Vite + React + TS + Tailwind + shadcn/ui + Recharts**（SaaS 控制台，见 [frontend/README.md](frontend/README.md)） |
| [**docs/**](docs/) | 产品文档（入口 [docs/README.md](docs/README.md)） |
| [docker-compose.yml](docker-compose.yml) | 本地 **Postgres + Redis**（前后端开发共用） |

## 文档索引

**推荐从 [docs/README.md](docs/README.md) 进入**（四步流程 + 六大指标速查 + 文档地图）。

| 文档 | 说明 |
|------|------|
| [docs/README.md](docs/README.md) | **文档总索引**（`NN-` 前缀见该目录说明） |
| [docs/01-项目说明.md](docs/01-项目说明.md) | 背景、定位、范围、术语 |
| [docs/02-竞品对标.md](docs/02-竞品对标.md) | SheepGeo / Dageno 能力对照 |
| [docs/03-需求说明.md](docs/03-需求说明.md) | 需求与约束 |
| [docs/04-功能清单.md](docs/04-功能清单.md) | 功能 ID，按四步编排（对标见 §9–§10） |
| [docs/05-诊断流程.md](docs/05-诊断流程.md) | 诊断四步：Verify / Dispatch / Clean / Analysis |
| [docs/06-分析指标.md](docs/06-分析指标.md) | 看板六大指标公式与实现说明 |
| [docs/07-后端联调.md](docs/07-后端联调.md) | 后端验收与 API 联调顺序 |

## 技术栈（后端已定）

见 [backend/README.md](backend/README.md) 与根目录历史说明：**Python / FastAPI / SQLAlchemy / Alembic / Celery / Redis**。

## 快速开始（后端）

```bash
docker compose up -d
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env   # 按需填写
export PYTHONPATH=src
python -m alembic upgrade head
python -m aperix_geo
# 另开终端，仍在 backend/：celery -A aperix_geo.celery_app.celery_app worker --loglevel=INFO
```

也可在**仓库根**使用同一虚拟环境：`pip install -e './backend[dev]'`，迁移与 Alembic 仍建议在 `backend/` 下执行（见 [backend/README.md](backend/README.md)）。

OpenAPI：`http://localhost:8000/docs`

## 快速开始（前端）

```bash
cd frontend
npm install
npm run dev
```

默认 **http://127.0.0.1:5173**；`/api`、`/health` 等已代理到本机 **8000** 端口后端（见 [frontend/README.md](frontend/README.md)）。

## 核心产品差异

- **地域**：聚焦中国大陆场景。  
- **监测主体**：支持 **域名** 与 **品牌关键词**（无独立站客户），见 [docs/01-项目说明.md](docs/01-项目说明.md)。

## 状态

后端 MVP 已可用；前端目录已预留，待选型后独立初始化。
