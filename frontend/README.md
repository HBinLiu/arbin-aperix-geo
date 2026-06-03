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
| 路由 | **React Router 6** | `/` 官网；`/app` 控制台（`RequireAuth`，无 JWT 重定向登录）；`/auth/*` 鉴权 |
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
cp .env.example .env   # 可选：仅当代码里使用 VITE_* 变量时需要
npm install
npm run dev
```

浏览器默认 **http://127.0.0.1:5173** 打开 **官网**（`/`）；**租户控制台**在 **`/app`**（无 token 会重定向到 **`/auth/login?next=/app`**）。**邮箱**：`/auth/register` 用验证码+密码注册，`/auth/login` 用邮箱+密码登录。**手机号**：仅在 `/auth/login` 选「手机号」发登录验证码，未注册号码验证通过即自动注册。后端默认 **`ENV=development`** 时手机号随机验证码并回显 **`dev_code`**，不发送真实短信；生产请设为 **`ENV=production`**。开发环境下邮箱注册验证码也会在 **`dev_code`** 回显。

---

## 环境变量

- **`VITE_API_BASE_URL`**：若将来在浏览器里直连完整后端 URL（不经代理），可在代码里读取；当前示例页使用**相对路径 + 代理**，可不填。

---

## 与后端约定

- OpenAPI：`/openapi.json`；鉴权：`Authorization: Bearer <token>` 或 `X-API-Key`（见 `../backend/.env.example`）。
- 生产部署：静态资源可挂 CDN；生产环境请收紧后端 **CORS**（勿长期 `*`）。

---

**文档版本**：0.5（可运行脚手架）  
**最后更新**：2026-05-15
