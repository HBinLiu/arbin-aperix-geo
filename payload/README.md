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
| SEO | `@payloadcms/plugin-seo` 挂在 `page-seo`；官网 BaseLayout 按 path 合并 |
| 草稿 / 发布 | FAQ、关于我们支持 draft；**Publish 后**官网 SSR 拉已发布内容 |
| FAQ 默认内容 | `shared/faq/defaults.ts`；`npm run seed` 写入 CMS；留空时官网 `mergeFaqs` 回退 |

## 本地开发

```bash
cd payload && cp .env.example .env && npm install
npm run dev
npm run seed          # 首次
```

```bash
cd website && npm run dev
```

## 常用命令

```bash
npm run generate:importmap
npm run generate:types
npm run repair:schema
npm run seed
npm run seed:force
```

## API 验证

```bash
curl -s 'http://127.0.0.1:3000/cms/api/globals/about-page' | jq .
curl -s 'http://127.0.0.1:3000/cms/api/faqs?where[page][equals]=home&limit=1' | jq '.docs[0].items'
curl -s 'http://127.0.0.1:3000/cms/api/faqs?where[page][equals]=pricing&limit=1' | jq '.docs[0].items'
curl -s 'http://127.0.0.1:3000/cms/api/faqs?where[page][equals]=platform/answer-engine-insights&limit=1' | jq '.docs[0].items'
curl -s 'http://127.0.0.1:3000/cms/api/page-seo?limit=20' | jq .
```
