# Aperix 官网（Astro）

静态营销站。首页文案与区块数据在 `src/lib/home.ts` 中维护；构建时仅从 Payload `/cms/api` 拉取 **站点设置**（站点名称、描述、默认 SEO）。Payload 未启动时使用 `home.ts` 中的默认值。

## 本地开发

```bash
cd website
cp .env.example .env
npm install
npm run dev
```

默认 <http://127.0.0.1:4321>。

开发代理（`astro.config.mjs`）：

| 路径 | 目标 |
|------|------|
| `/api/*` | FastAPI `:8000` |
| `/cms/api/*` | Payload `:3000` |

建议同时启动：

```bash
# 终端 1：Payload
cd payload && npm run dev

# 终端 2：官网
cd website && npm run dev

# 终端 3（可选）：控制台
cd frontend && npm run dev
```

## 构建

```bash
npm run build   # 输出 dist/
npm run preview
```

生产部署时由反向代理将 `/` 指向 `website/dist`，`/app` 与 `/auth` 指向 React SPA，`/api/v1` 指向 FastAPI，`/cms` 指向 Payload。

## 环境变量

| 变量 | 说明 |
|------|------|
| `PUBLIC_PAYLOAD_URL` | Payload REST 根路径，默认经 dev proxy 的 `/cms/api` |
| `PUBLIC_API_URL` | 产品 API（定价页等，P2） |
