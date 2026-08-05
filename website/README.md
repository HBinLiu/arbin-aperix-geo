# Aperix 官网（Astro）

静态营销站。站点配置在 `site.config.mjs`（`@site` 引用）；首页文案在 `src/lib/home.ts`，SEO 在 `src/lib/seo.ts`；**关于页 story** 与 **首页 FAQ** 可选从 Payload 拉取；定价从 FastAPI 拉取。

## 本地开发

```bash
cd website
cp .env.example .env.development
npm install
npm run dev
```

默认 <http://127.0.0.1:4321>。Astro 按 mode 加载：`dev` → `.env.development`；`build` → `.env.production`。

- **Payload**：`PAYLOAD_API_URL=/cms/api`（开发时映射到 `:3000`；生产同域）
- **产品 API**：`BACKEND_API_URL` 直连 FastAPI `:8000`
- **控制台 CTA**：`PUBLIC_LOGIN_URL` / `PUBLIC_REGISTER_URL` 本地指向 `http://127.0.0.1:5173/auth/login`；生产指向 `https://app.aperix.cn/auth/login`
- **国内站长验证**（可选）：在站长后台选「HTML 标签验证」后，把 code 写入 `.env`（如 `PUBLIC_BAIDU_SITE_VERIFICATION`）或 `site.config.mjs` 的 `siteVerification`；空值不输出
- **头条自动收录**（可选）：站长后台「数据提交 → 自动收录」的 `push.js?` token，写入 `site.config.mjs` 的 `bytedancePushToken` 或 `PUBLIC_BYTEDANCE_PUSH_TOKEN`；注入全站 `<head>`（`noindex` 页除外）

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

生产部署：营销域（如 `aperix.cn`）`/` → website Node；`/cms` → Payload。控制台域 **`app.aperix.cn`** → frontend 静态 `dist`，同域 `/api` → FastAPI。详见 [docs/10-部署说明.md](../docs/10-部署说明.md)。

## 站点地图（Sitemap）与各搜索引擎提交

全站单一 SSR urlset：`/sitemap.xml`（营销页代码清单 + 请求时拉取 CMS 已发布详情）。CMS 发布后无需 rebuild 即可进入 sitemap。

| 路径 | 说明 |
|------|------|
| `{origin}/sitemap.xml` | 全站单一 urlset（营销页 + CMS 详情） |

`robots.txt` 声明：

```txt
Sitemap: {origin}/sitemap.xml
```

### 各平台填写方式

| 平台 | 控制台 | 提交的 Sitemap URL |
|------|--------|-------------------|
| **Google / Bing** | Search Console / Webmaster | `{origin}/sitemap.xml` |
| **百度 / 头条 / 360** | 各站长平台 | `{origin}/sitemap.xml`（urlset） |

**生产部署：** `/sitemap.xml` 依赖 Node adapter 与 Payload API；反向代理需把该路由转到 website Node 进程。

### 其他 SEO 产物

| 路径 | 说明 |
|------|------|
| `{origin}/robots.txt` | 由 `src/pages/robots.txt.ts` 生成 |
| `{origin}/llms.txt` | 面向 AI 爬虫的站点摘要（`src/pages/llms.txt.ts`） |

Sitemap 仅帮助爬虫发现 URL，不保证收录或排名。

**百度 API 主动推送：** CMS 详情在 Payload 发布时自动推；营销页在官网部署后于 `payload` 执行 `npm run baidu:push-static`（读线上 `/sitemap.xml`）。详见 `payload/README.md`。

**头条/抖音自动收录：** 配置 `bytedancePushToken` 后，用户浏览页面时由官方 `ttzz/push.js` 提交当前 URL；与后台 Sitemap 提交互不冲突。站长后台仍需提交 `{origin}/sitemap.xml`。

**IndexNow：** `site.config.mjs` 的 `indexNowKey` + `website/public/{key}.txt`。CMS 发布时自动推；营销页部署后于 `payload` 执行 `npm run indexnow:push-static`。详见 `payload/README.md`。

## 环境变量

| 变量 | 说明 |
|------|------|
| `PAYLOAD_API_URL` | Payload REST 路径，默认 `/cms/api` |
| `BACKEND_API_URL` | 产品 API 根路径，如 `http://127.0.0.1:8000/api/v1`（定价页 `/billing/plans`） |
