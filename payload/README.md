# Aperix Payload CMS

营销内容后台（Payload 3 + PostgreSQL）。公网路径：

- Admin：`/cms`
- REST API：`/cms/api`

## 架构

采用 Payload 官方 Website Template 推荐的 **Global + Collection 混合**模式：

| 类型 | 用途 | 示例 |
|------|------|------|
| **Global** | 单页 singleton，侧边栏直达 | `about-page` 关于页 |
| **Collection** | 可排序、可增删的实体列表 | `faqs` 首页 FAQ |

```
官网内容/
├── 关于页          ← Global（故事 + SEO，草稿/发布）
└── FAQ            ← Collection（page=home，sortOrder 排序）
```

## 前置

在**与产品库 `arbin_aperix_geo` 同一 Postgres 实例**上手动创建 CMS 库（不用 Docker 时）：

```sql
CREATE DATABASE arbin_aperix_cms;
```

若使用仓库根目录 `docker compose up -d`，Postgres 首次启动会通过 `scripts/init-cms-db.sh` 自动建库。

## 本地开发

```bash
cd payload
cp .env.example .env
npm install
npm run dev
npm run seed    # 首次建议执行
```

- Admin：<http://localhost:3000/cms>
- API：<http://localhost:3000/cms/api/globals/about-page>、<http://localhost:3000/cms/api/faqs>

## 内容模型

| 类型 | slug | 说明 |
|------|------|------|
| Global | `about-page` | 关于页：我们的故事 + SEO |
| Collection | `faqs` | 首页 FAQ（`page=home`） |
| Collection | `media` | 图片 |
| Collection | `users` | CMS 管理员 |

文案中可用 `{{name}}` 占位符，官网渲染时替换为品牌名。

## 访问控制

| 资源 | 匿名读 | 写 |
|------|--------|-----|
| `about-page` Global | 仅 `_status=published` | 需登录 |
| `faqs` / `media` | ✅ | 需登录 |
| `users` | ❌ | 需登录 |

官网无 CMS 登录态；CMS 未启动或无数据时回退 `about.ts` / `home.ts` 静态文案。

## 运营指引

### 关于页（Global）

1. 侧边栏 **官网内容 → 关于页**，直接进入编辑（无需在列表里找 slug）
2. Tab：**SEO** / **我们的故事**
3. 右上角 **Publish** 后官网 `/about` 才展示 CMS 内容

### 首页 FAQ（Collection）

1. **官网内容 → FAQ**，逐条新增
2. **页面** 选「首页」，`sortOrder` 越小越靠前
3. CMS 无 home FAQ 时，官网回退 `home.ts` 默认四条

## 常用命令

```bash
npm run generate:importmap
npm run generate:types
npm run seed                 # 跳过已有数据
npm run seed:force           # 覆盖 about Global + 重建 home FAQ
npm run build && npm start
```

## 初始化与迁移

### 首次部署

```bash
cd payload && cp .env.example .env && npm install
npm run dev    # 同步表结构；/cms 创建管理员
npm run seed
```

### 从旧版 `pages` Collection 升级

旧版用 `pages` Collection（`slug=about`）管理关于页，现已改为 **`about-page` Global**。

1. 重启 `npm run dev` 同步新 schema
2. 若旧 `pages` 表有自定义内容，请在 Admin 手动复制到 **关于页 Global**，或 `npm run seed:force` 用默认文案覆盖
3. 可选：删除废弃的 `pages` 表（确认无需要保留的数据后）

```sql
-- 可选清理（确认后执行）
DROP TABLE IF EXISTS pages CASCADE;
DROP TABLE IF EXISTS _pages_v CASCADE;
```

### 验证

```bash
curl -s 'http://127.0.0.1:3000/cms/api/globals/about-page' | jq .
curl -s 'http://127.0.0.1:3000/cms/api/faqs?where[page][equals]=home&sort=sortOrder&limit=10' | jq .
```
