# Aperix 官网（Astro）

静态营销站。首页文案与区块数据在 `src/lib/home.ts` 中维护；构建时从 Payload 拉取 **站点设置**，从 FastAPI 拉取 **定价计划**。

## 本地开发

```bash
cd website
cp .env.example .env
npm install
npm run dev
```

默认 <http://127.0.0.1:4321>。

- **Payload**：`PAYLOAD_API_URL=/cms/api`（与生产同域；本地 dev 解析为 `:3000`）
- **产品 API**：`BACKEND_API_URL` 直连 FastAPI `:8000`

建议同时启动：

```bash
# 终端 1：Payload
cd payload && npm run dev

# 终端 2：Backend（定价页必需）
cd backend && uvicorn aperix_geo.main:app --reload --port 8000

# 终端 3：官网
cd website && npm run dev

# 终端 4（可选）：控制台
cd frontend && npm run dev
```

## 构建

```bash
npm run build   # 输出 dist/；需 backend :8000 可访问（见 BACKEND_API_URL）
npm run preview
```

生产部署时由反向代理将 `/` 指向 `website/dist`，`/app` 与 `/auth` 指向 React SPA，`/api/v1` 指向 FastAPI，`/cms` 指向 Payload。

## 环境变量

| 变量 | 说明 |
|------|------|
| `PAYLOAD_API_URL` | Payload REST 路径，默认 `/cms/api`（生产同域；本地 build 拼 `site` 域名） |
| `BACKEND_API_URL` | 产品 API 根路径，如 `http://127.0.0.1:8000/api/v1`（定价页 `/billing/plans`） |
