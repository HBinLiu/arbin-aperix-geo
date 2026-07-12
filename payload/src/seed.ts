import { getPayload } from "payload";
import config from "@payload-config";
import { ABOUT_STORY_PARAGRAPHS, ABOUT_STORY_TITLE } from "@shared/about";
import { faqP } from "@shared/faq/defaults";
import { defaultPageSeoEntries } from "@shared/seo/defaults/entries";

import { htmlToLexical } from "./seed/rich-text";
import { faqSeedGroups } from "./seed/faqs";
import { researchCategorySeedItems } from "./seed/researches";

const defaultAboutStoryHtml = faqP(...ABOUT_STORY_PARAGRAPHS);

const ABOUT_GLOBAL_SLUG = "about-page";
const PAGE_SEO_COLLECTION = "page-seo";
const FAQ_COLLECTION = "faqs";
const force = process.argv.includes("--force");

function log(message: string) {
  process.stderr.write(`${message}\n`);
}

function hasAboutContent(data: {
  story?: { content?: unknown } | null;
}) {
  const content = data.story?.content;
  if (!content || typeof content !== "object") return false;
  const root = (content as { root?: { children?: unknown[] } }).root;
  return (root?.children?.length ?? 0) > 0;
}

async function seedAboutPage(payload: Awaited<ReturnType<typeof getPayload>>) {
  const existing = await payload.findGlobal({
    slug: ABOUT_GLOBAL_SLUG,
    depth: 0,
  });

  if (hasAboutContent(existing) && !force) {
    log("⏭  关于我们已有内容，跳过。使用 --force 覆盖。");
    return;
  }

  await payload.updateGlobal({
    slug: ABOUT_GLOBAL_SLUG,
    data: {
      _status: "published",
      story: {
        title: ABOUT_STORY_TITLE,
        content: await htmlToLexical(defaultAboutStoryHtml),
      },
    },
  });
  log("✅ 关于我们 Global 已写入（_status=published）");
}

async function seedPageSeo(payload: Awaited<ReturnType<typeof getPayload>>) {
  let created = 0;
  let updated = 0;
  let skipped = 0;

  for (const entry of defaultPageSeoEntries) {
    const existing = await payload.find({
      collection: PAGE_SEO_COLLECTION,
      where: { path: { equals: entry.path } },
      limit: 1,
      depth: 0,
    });
    const doc = existing.docs[0];

    if (doc) {
      if (force) {
        await payload.update({
          collection: PAGE_SEO_COLLECTION,
          id: doc.id,
          data: {
            label: entry.label,
            path: entry.path,
            noindex: entry.noindex ?? false,
            meta: entry.meta,
          },
        });
        updated += 1;
      } else {
        skipped += 1;
      }
      continue;
    }

    await payload.create({
      collection: PAGE_SEO_COLLECTION,
      data: {
        label: entry.label,
        path: entry.path,
        noindex: entry.noindex ?? false,
        meta: entry.meta,
      },
    });
    created += 1;
  }

  if (created === 0 && updated === 0) {
    log(`⏭  SEO设置 seed 已存在（${skipped} 条），跳过。使用 --force 仅同步默认 path 条目。`);
    return;
  }

  const parts = [`新增 ${created} 条`];
  if (updated > 0) parts.push(`更新 ${updated} 条`);
  log(`✅ SEO设置已写入（${parts.join("，")}；不删除手动添加的页面）`);
}

async function seedFaqs(payload: Awaited<ReturnType<typeof getPayload>>) {
  let created = 0;
  let updated = 0;
  let skipped = 0;
  let writtenItems = 0;

  for (const group of faqSeedGroups) {
    const items = await Promise.all(
      group.items.map(async (item) => ({
        question: item.question,
        ...(item.label ? { label: item.label } : {}),
        answer: await htmlToLexical(item.answerHtml),
      })),
    );

    const existing = await payload.find({
      collection: FAQ_COLLECTION,
      where: { page: { equals: group.page } },
      limit: 1,
      depth: 0,
    });
    const doc = existing.docs[0];

    if (doc) {
      if (force) {
        await payload.update({
          collection: FAQ_COLLECTION,
          id: doc.id,
          data: {
            _status: "published",
            label: group.label,
            page: group.page,
            items,
          },
        });
        updated += 1;
        writtenItems += items.length;
      } else {
        skipped += 1;
      }
      continue;
    }

    await payload.create({
      collection: FAQ_COLLECTION,
      data: {
        _status: "published",
        label: group.label,
        page: group.page,
        items,
      },
    });
    created += 1;
    writtenItems += items.length;
  }

  if (created === 0 && updated === 0) {
    log(`⏭  常见问题 seed 已存在（${skipped} 页），跳过。使用 --force 仅同步默认 page 条目。`);
    return;
  }

  const parts = [`新增 ${created} 页`];
  if (updated > 0) parts.push(`更新 ${updated} 页`);
  log(
    `✅ 常见问题已写入（${parts.join("，")}，共 ${writtenItems} 条；不删除手动添加的 FAQ 页）`,
  );
}

const RESEARCH_CATEGORY_COLLECTION = "research-categories";

async function seedResearchCategories(payload: Awaited<ReturnType<typeof getPayload>>) {
  let created = 0;
  let updated = 0;
  let skipped = 0;

  for (const item of researchCategorySeedItems) {
    const existing = await payload.find({
      collection: RESEARCH_CATEGORY_COLLECTION,
      where: { slug: { equals: item.slug } },
      limit: 1,
      depth: 0,
    });
    const doc = existing.docs[0];

    if (doc) {
      if (force) {
        await payload.update({
          collection: RESEARCH_CATEGORY_COLLECTION,
          id: doc.id,
          data: {
            label: item.label,
            sortOrder: item.sortOrder ?? 0,
          },
        });
        updated += 1;
      } else {
        skipped += 1;
      }
      continue;
    }

    await payload.create({
      collection: RESEARCH_CATEGORY_COLLECTION,
      data: {
        slug: item.slug,
        label: item.label,
        sortOrder: item.sortOrder ?? 0,
      },
    });
    created += 1;
  }

  if (created === 0 && updated === 0) {
    log(`⏭  研究分类 seed 已存在（${skipped} 条），跳过。使用 --force 仅同步默认 label/sortOrder。`);
    return;
  }

  const parts = [`新增 ${created} 条`];
  if (updated > 0) parts.push(`更新 ${updated} 条`);
  log(`✅ 研究分类已写入（${parts.join("，")}；不删除手动添加的分类或报告）`);
}

const payload = await getPayload({ config });

log(force ? "🌱 开始 seed（--force 同步代码默认项，不删除手动添加的数据）…" : "🌱 开始 seed（跳过已有默认项）…");

await seedAboutPage(payload);
await seedPageSeo(payload);
await seedFaqs(payload);
await seedResearchCategories(payload);

log("🎉 Seed 完成");

process.exit(0);
