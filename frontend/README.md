# Aperix AI — 前端

与 `../backend/` **完全隔离**（独立依赖、独立构建与部署），仅通过 **HTTP** 访问后端 API（默认前缀 `http://<host>:<port>/api/v1`）。

**定位**：基于 **React + Vite + Tailwind CSS + Radix UI（shadcn/ui）+ Recharts** 的 **SaaS 仪表板**（控制台）应用。

---

## 技术栈（已定）

| 层级 | 选型 | 说明 |
|------|------|------|
| 构建 | **Vite 6** | SPA；`npm run dev` / `npm run build` |
| 框架 | **React 18** + **TypeScript 5** | 与 shadcn/ui、Recharts 同生态 |
| 样式 | **Tailwind CSS 4.x** + **PostCSS**（`@tailwindcss/postcss`） | 主题 token 在 `src/index.css` 的 `@theme`；**tailwindcss-animate** 经 `@plugin` 引入 |
| 组件 | **Radix UI + shadcn/ui**（new-york） | `components.json` 已配置；当前含 `button`、`card`，更多组件：`npx shadcn@latest add tabs` 等 |
| 图表 | **Recharts** | 首页含示例折线图 |
| 服务端状态 | **TanStack Query v5** | 已在 `App` 根挂载 `QueryClientProvider` |
| 路由 | **React Router 6** | `/` 控制台（`RequireAuth`）；`/auth/*` 鉴权；生产挂 `app.aperix.cn` |
| HTTP | **axios**（依赖已装，可按需封装 `src/lib/api.ts`） | 与 `fetch` 二选一统一即可 |
| API 类型 | **OpenAPI 生成**（可选） | `openapi-typescript` + `openapi-fetch` 未默认安装，需要时 `npm add -D openapi-typescript openapi-fetch` |
| 质量 | **ESLint 9** + **typescript-eslint** | `npm run lint` |

### 开发代理（`vite.config.ts`）

为减少 CORS 摩擦，已将 **`/api`**、**`/openapi.json`**、**`/docs`**、**`/health`** 代理到 **`http://127.0.0.1:8000`**。前端页面里可直接写 `fetch("/health")`。

### 竞品技术观察（Dageno）

- **dageno.ai 营销站**：HTML 可见 **Next.js App Router**。  
- **图表**：对方产品侧为 **Recharts** — 与本仓库一致。控制台仍为 **Vite SPA**。

### 首期不采用的方案（保留记录）

| 方案 | 理由 |
|------|------|
| **Next.js** | 控制台 MVP 以 **CSR + Vite** 为主。 |
| **Ant Design / MUI** | 与 **shadcn + Tailwind** 二选一，已定后者。 |
| **Apache ECharts** | 与 **Recharts** 重复；特殊大屏需求后续再议。 |

---

## 本地运行

```bash
cd frontend
cp .env.example .env.development   # 可选：仅当使用 VITE_* 时需要
npm install
npm run dev
```

浏览器默认 **http://127.0.0.1:5173**：未登录进 **`/auth/login`**，登录后进控制台 **`/`**（如 `/billing/plan`）。登录页支持 **手机号** 或 **邮箱** 验证码登录；未注册账号在验证通过后自动开通。后端默认 **`ENV=development`** 时邮箱/手机均不真实发送，响应回显 **`dev_code`**；生产请设 **`ENV=production`**，并配置 **SMTP_***（邮箱）与 **SMS_ALIYUN_***（手机）。

生产构建：`npm run build` → `dist/`；用 Nginx 托管到 **`app.aperix.cn`**，并将 `/api` 反代到 FastAPI。也可用仓库根目录 [`rebuild-and-restart-frontend.sh`](../rebuild-and-restart-frontend.sh)。部署总览与 Node 22 离线导入见 [docs/10-部署说明.md](../docs/10-部署说明.md)。

---

## 环境变量

Vite 按 mode 加载：`npm run dev` → `.env.development`；`npm run build` → `.env.production`（从 `.env.example` 复制后填写）。

- **`VITE_API_BASE_URL`**：若将来在浏览器里直连完整后端 URL（不经代理），可在代码里读取；当前示例页使用**相对路径 + 代理**，可不填。

---

## 与后端约定

- OpenAPI：`/openapi.json`；鉴权：`Authorization: Bearer <token>` 或 `X-API-Key`（见 `../backend/.env.development`）。
- 生产：静态 `dist` 挂 `app.aperix.cn`；API 同域 `/api/v1`；可按需收紧后端 CORS。

---

**文档版本**：0.5（可运行脚手架）  
**最后更新**：2026-05-15
