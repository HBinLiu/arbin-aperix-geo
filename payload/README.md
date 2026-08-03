# Aperix Payload CMS

营销内容后台（Payload 3 + PostgreSQL）。公网路径：`/cms`（Admin）、`/cms/api`（REST）。

## 架构

Admin 侧边栏 **站点设置**（Payload 默认：Collections 先于 Globals）：

```
站点设置/
├── 常见问题        ← Collection `faqs`（首页、定价、平台能力、监测页）
├── SEO设置         ← Collection `page-seo`（各页 meta）
└── 关于我们        ← Global `about-page`（我们的故事）
```

| 能力 | 实现 |
|------|------|
| SEO | `@payloadcms/plugin-seo` 挂在 `page-seo`（含 keywords）与内容集合；官网 BaseLayout 按 path 合并 |
| 草稿 / 发布 | FAQ、关于我们支持 draft；**Publish 后**官网按请求 SSR 拉取已发布内容（`/about` 已关闭静态预渲染） |
| FAQ 默认内容 | `shared/faq/defaults.ts`；`npm run seed` 写入 CMS；留空时官网 `mergeFaqs` 回退 |

## 本地开发

```bash
cd payload && cp .env.example .env.development && npm install
npm run seed          # 首次：自动 push schema + 写入默认内容
npm run dev
```

Next 按 mode 加载：`dev` → `.env.development`；`build` / `start` → `.env.production`。生产构建使用 `next build --webpack`。小内存 ECS 上易 **OOM → SIGKILL**：[`rebuild-and-restart-payload.sh`](../rebuild-and-restart-payload.sh) 会自动补 swap、构建前 stop website/payload、`NEXT_BUILD_CPUS=1` + `webpackBuildWorker`、按内存选 `--max-old-space-size`（勿盲目设 4096）。仍失败则在内存更大的机器构建后把 `payload/.next` 拷到服务器，或加物理内存。

本地上传的媒体文件落在 **`payload/media/`**（`Media` collection `staticDir`）。该目录**纳入 Git**，发布时随 `git pull` 到服务器；勿再加入 `.gitignore`，否则线上 CMS / 官网图片会缺失。

`seed` 启动时会调用 `getPayload()`，Payload 会自动将 schema push 到 PostgreSQL（空库会建表，已有库会增量对齐）。**不需要单独的 schema 初始化脚本。**

```bash
cd website && npm run dev
```

## 常用命令

```bash
npm run generate:importmap
npm run generate:types
npm run seed          # 补写缺失的默认 FAQ / SEO / 分类（不删已有数据）
npm run seed:force    # 同步代码默认项到 CMS（不删手动添加的条目）
```

## Schema 冲突怎么办

本项目使用 Payload Drizzle **push**（无 migration 文件）。若本地库残留旧结构导致 push 失败：

1. **推荐**：删掉本地 CMS 库重建（如 `dropdb && createdb …`），再 `npm run seed`
2. 生产环境：改 schema 前应备份，必要时引入 Payload migrations

## API 验证

```bash
curl -s 'http://127.0.0.1:3000/cms/api/globals/about-page' | jq .
curl -s 'http://127.0.0.1:3000/cms/api/faqs?where[page][equals]=home&limit=1' | jq '.docs[0].items'
curl -s 'http://127.0.0.1:3000/cms/api/faqs?where[page][equals]=pricing&limit=1' | jq '.docs[0].items'
curl -s 'http://127.0.0.1:3000/cms/api/faqs?where[page][equals]=platform/answer-engine-insights&limit=1' | jq '.docs[0].items'
curl -s 'http://127.0.0.1:3000/cms/api/page-seo?limit=20' | jq .
```

## 百度普通收录 API 推送

配置 `BAIDU_PUSH_SITE` / `BAIDU_PUSH_TOKEN`（从站长平台 → 普通收录 → API 的示例 curl **原样复制** `site` 与 `token`；你站若示例为 `site=https://www.aperix.cn` 则配置也带 `https://`）后：

1. **CMS 内容自动**：博客 / 新闻 / 学院 / 研究 / 更新日志 / 作者在**首次发布**或**改 slug** 时异步推送（需 `PUBLIC_WEBSITE_URL` 为 `https://`；本地 `http` 跳过）。
2. **官网营销页**：不走 CMS hook；部署后从线上 `/sitemap.xml` 拉取并推送。
   脚本会自行读取 `.env.production`（`payload run` 默认不加载该文件；仅改文件不会进已创建容器的 `--env-file`）。

```bash
# 生产（容器内）
docker exec -it aperix-payload npm run baidu:push-static
docker exec -it aperix-payload npm run baidu:push-all

# 本地
npm run baidu:push-static   # 仅营销页（排除 CMS 路径）
npm run baidu:push-all      # 全站 sitemap.xml（首次回填）
```

CMS **发布时自动推送**依赖 Next 进程环境：改完 `.env.production` 后需 `docker restart aperix-payload`（或重建容器）。

或已登录 CMS 后：

```bash
# 推送营销页
curl -X POST 'https://www.aperix.cn/cms/api/baidu-push' \
  -H 'Content-Type: application/json' \
  -H 'Cookie: <admin-session>' \
  -d '{"sitemap":"static"}'

# 指定 URL
curl -X POST 'https://www.aperix.cn/cms/api/baidu-push' \
  -H 'Content-Type: application/json' \
  -H 'Cookie: <admin-session>' \
  -d '{"urls":["https://www.aperix.cn/pricing/"]}'
```

日志前缀 `[baidu-push]`；日配额以站长平台「剩余额度」为准。站长后台提交 `{origin}/sitemap.xml` 即可。
