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

采用建站 skill **模式 A**：营销页走构建期 `@astrojs/sitemap`；CMS 栏目（博客 / 学院 / 研究 / 新闻 / Changelog / 作者）为 **SSR + 动态 sitemap**，后台发布后无需 rebuild 即可打开与进入动态 sitemap。

| 文件 | 类型 | 说明 |
|------|------|------|
| `sitemap-index.xml` / `sitemap-N.xml` | 静态 | 营销页等预渲染路由（已 filter 掉 CMS 路径） |
| `sitemap-blog.xml` 等 | 动态 SSR | 请求时查 Payload 全量已发布文档 |

站点域名以 `site.config.mjs` 的 `url` 为准。下文用 `{origin}` 表示该域名。

`src/pages/robots.txt.ts` 会声明：

```txt
Sitemap: {origin}/sitemap-index.xml
Sitemap: {origin}/sitemap-blog.xml
Sitemap: {origin}/sitemap-academy.xml
Sitemap: {origin}/sitemap-research.xml
Sitemap: {origin}/sitemap-news.xml
Sitemap: {origin}/sitemap-changelogs.xml
Sitemap: {origin}/sitemap-authors.xml
```

### 各平台填写方式

| 平台 | 控制台 | 提交的 Sitemap URL | 备注 |
|------|--------|-------------------|------|
| **Google** | [Search Console](https://search.google.com/search-console) → 站点地图 | `{origin}/sitemap-index.xml`，并分别提交各 `sitemap-<topic>.xml` | 支持索引型与动态 urlset |
| **Bing** | [Bing Webmaster](https://www.bing.com/webmasters) → Sitemaps | 同上 | |
| **百度** | [百度搜索资源平台](https://ziyuan.baidu.com) → 资源提交 → 普通收录 → sitemap | `{origin}/sitemap-0.xml` + 各 `sitemap-<topic>.xml` | **勿提交** `sitemap-index.xml`（会提示「索引型不予处理」） |
| **头条搜索** | [头条搜索站长平台](https://zhanzhang.toutiao.com) | 同百度，交最终 urlset | |
| **360** | [360 站长平台](https://zhanzhang.so.com) | 先试 index，异常则 `sitemap-0.xml` + 动态 topic | |
| **搜狗** | [搜狗站长平台](https://zhanzhang.sogou.com) | 同上 | |
| **神马 / 夸克** | [神马站长平台](https://zhanzhang.sm.cn) | `{origin}/sitemap-0.xml` + 各动态 topic | |

**百度 / 头条 / 神马注意：** 若曾误提交 `sitemap-index.xml`，请在对应后台删除，避免占配额且不处理。

**生产部署：** CMS SSR 与动态 sitemap 依赖 Node adapter（`astro build` 后的 server）；反向代理需把对应路由转到 website Node 进程，且能访问 Payload API。

### 其他 SEO 产物

| 路径 | 说明 |
|------|------|
| `{origin}/robots.txt` | 由 `src/pages/robots.txt.ts` 生成 |
| `{origin}/llms.txt` | 面向 AI 爬虫的站点摘要（`src/pages/llms.txt.ts`） |

Sitemap 仅帮助爬虫发现 URL，不保证收录或排名；国内平台还可配合各站长的 URL 手动提交、自动推送代码等能力。

## 环境变量

| 变量 | 说明 |
|------|------|
| `PAYLOAD_API_URL` | Payload REST 路径，默认 `/cms/api` |
| `BACKEND_API_URL` | 产品 API 根路径，如 `http://127.0.0.1:8000/api/v1`（定价页 `/billing/plans`） |
