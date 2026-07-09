# Aperix Payload CMS

营销内容后台（Payload 3 + PostgreSQL）。公网路径：

- Admin：`/cms`
- REST API：`/cms/api`

## 前置

在**与产品库 `arbin_aperix_geo` 同一 Postgres 实例**上手动创建 CMS 库（不用 Docker 时）：

```sql
CREATE DATABASE arbin_aperix_cms;
```

或用 psql 一行命令（按你的连接信息替换 host/user）：

```bash
psql "postgresql://aperix:<password>@<host>:5432/arbin_aperix_geo" \
  -c "CREATE DATABASE arbin_aperix_cms;"
```

若使用仓库根目录 `docker compose up -d`，Postgres 首次启动会通过 `scripts/init-cms-db.sh` 自动建库。

## 本地开发

```bash
cd payload
cp .env.example .env
npm install
npm run dev
```

- Admin：<http://localhost:3000/cms>
- API：<http://localhost:3000/cms/api/pages>

首次访问 `/cms` 按提示创建管理员账号。

## 内容模型

| 类型 | slug | 说明 |
|------|------|------|
| Collection | `pages` | 落地页（slug: `home` / `pricing` / `about`） |
| Collection | `faqs` | FAQ 条目 |
| Global | `site-settings` | 导航、页脚、默认 SEO |
| Collection | `media` | 图片 |
| Collection | `users` | CMS 管理员 |

## 常用命令

```bash
npm run generate:importmap   # 更新 Admin importMap
npm run generate:types       # 生成 payload-types.ts
npm run build && npm start   # 生产构建
```
