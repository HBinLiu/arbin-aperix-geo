# Aperix 官网（Astro）

静态营销站。站点配置在 `site.config.mjs`（`@site` 引用）；首页文案在 `src/lib/home.ts`，SEO 在 `src/lib/seo.ts`；**关于页 story** 与 **首页 FAQ** 可选从 Payload 拉取；定价从 FastAPI 拉取。

## 本地开发

```bash
cd website
cp .env.example .env
npm install
npm run dev
```

默认 <http://127.0.0.1:4321>。

- **Payload**：`PAYLOAD_API_URL=/cms/api`（关于页 story、首页 FAQ；本地 dev 解析为 `:3000`）
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

## 站点地图（Sitemap）与各搜索引擎提交

构建后 `@astrojs/sitemap` 会在 `dist/` 生成两类文件（符合 [sitemap.org](https://www.sitemaps.org/) 规范）：

| 文件 | 类型 | 说明 |
|------|------|------|
| `sitemap-index.xml` | 索引 | 指向一个或多个子 sitemap |
| `sitemap-0.xml` | URL 列表 | 当前全站页面均在此文件（`<urlset>`） |

站点域名以 `site.config.mjs` 的 `url` 为准（当前为 `https://aperix.ai`）。下文用 `{origin}` 表示该域名。

`src/pages/robots.txt.ts` 会向 Google / Bing 等爬虫声明：

```txt
Sitemap: {origin}/sitemap-index.xml
```

这是国际搜索引擎的常规入口，**无需为百度单独改 robots.txt**。

### 各平台填写方式

| 平台 | 控制台 | 提交的 Sitemap URL | 备注 |
|------|--------|-------------------|------|
| **Google** | [Search Console](https://search.google.com/search-console) → 站点地图 | `{origin}/sitemap-index.xml` | 支持索引型 |
| **Bing** | [Bing Webmaster](https://www.bing.com/webmasters) → Sitemaps | `{origin}/sitemap-index.xml` | 支持索引型 |
| **百度** | [百度搜索资源平台](https://ziyuan.baidu.com) → 资源提交 → 普通收录 → sitemap | `{origin}/sitemap-0.xml` | **勿提交** `sitemap-index.xml`（会提示「索引型不予处理」） |
| **头条搜索** | [头条搜索站长平台](https://zhanzhang.toutiao.com) → 数据提交 → 链接提交 → sitemap 提交 | `{origin}/sitemap-0.xml` | 支持 XML / TXT；单文件 ≤1 万 URL、≤10MB。与百度类似，提交含 URL 的最终 xml，勿交索引文件 |
| **360** | [360 站长平台](https://zhanzhang.so.com) | 先试 `{origin}/sitemap-index.xml`，若异常则改 `{origin}/sitemap-0.xml` | |
| **搜狗** | [搜狗站长平台](https://zhanzhang.sogou.com) | 同上 | |
| **神马 / 夸克** | [神马站长平台](https://zhanzhang.sm.cn) → Sitemap 提交 | `{origin}/sitemap-0.xml` | 阿里系移动搜索；夸克无独立站长台，与神马共用抓取。建议交最终 urlset，并配合「链接提交 / 实时推送」 |

**百度 / 头条 / 神马注意：** 若曾误提交 `sitemap-index.xml`，请在对应后台删除，避免占配额且不处理。

**站点变大后：** Astro 可能额外生成 `sitemap-1.xml`、`sitemap-2.xml` …  
- Google / Bing：仍只提交 `{origin}/sitemap-index.xml`  
- 百度 / 头条 / 神马：将每个 `sitemap-N.xml` **分别提交**（不要提交 index）

### 其他 SEO 产物

| 路径 | 说明 |
|------|------|
| `{origin}/robots.txt` | 由 `src/pages/robots.txt.ts` 生成 |
| `{origin}/llms.txt` | 面向 AI 爬虫的站点摘要（`src/pages/llms.txt.ts`） |

Sitemap 仅帮助爬虫发现 URL，不保证收录或排名；国内平台还可配合各站长的 URL 手动提交、自动推送代码等能力。

## 环境变量

| 变量 | 说明 |
|------|------|
| `PAYLOAD_API_URL` | Payload REST 路径，默认 `/cms/api`（生产同域；本地 build 拼 `site` 域名） |
| `BACKEND_API_URL` | 产品 API 根路径，如 `http://127.0.0.1:8000/api/v1`（定价页 `/billing/plans`） |
