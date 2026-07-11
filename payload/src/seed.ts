import { getPayload } from "payload";
import config from "@payload-config";
import { ABOUT_STORY_PARAGRAPHS, ABOUT_STORY_TITLE } from "@shared/about";
import { faqP } from "@shared/faq/defaults";
import { defaultPageSeoEntries } from "@shared/seo/defaults";

import { htmlToLexical } from "./seed/rich-text";
import { faqSeedCount, faqSeedGroups, faqSeedPageCount } from "./seed/faqs";

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
  const existing = await payload.find({
    collection: PAGE_SEO_COLLECTION,
    limit: 1,
    depth: 0,
  });

  if (existing.totalDocs > 0 && !force) {
    log(`⏭  SEO设置已有 ${existing.totalDocs} 条，跳过。使用 --force 覆盖。`);
    return;
  }

  if (force && existing.totalDocs > 0) {
    while (true) {
      const batch = await payload.find({
        collection: PAGE_SEO_COLLECTION,
        limit: 100,
        depth: 0,
      });
      if (batch.docs.length === 0) break;
      for (const doc of batch.docs) {
        await payload.delete({ collection: PAGE_SEO_COLLECTION, id: doc.id });
      }
    }
  }

  for (const entry of defaultPageSeoEntries) {
    await payload.create({
      collection: PAGE_SEO_COLLECTION,
      data: {
        label: entry.label,
        path: entry.path,
        noindex: entry.noindex ?? false,
        meta: entry.meta,
      },
    });
  }

  log(`✅ SEO设置已写入 ${defaultPageSeoEntries.length} 条`);
}

async function seedFaqs(payload: Awaited<ReturnType<typeof getPayload>>) {
  const existing = await payload.find({
    collection: FAQ_COLLECTION,
    limit: 1,
    depth: 0,
  });

  if (existing.totalDocs > 0 && !force) {
    log(`⏭  常见问题已有 ${existing.totalDocs} 条，跳过。使用 --force 覆盖。`);
    return;
  }

  if (force && existing.totalDocs > 0) {
    while (true) {
      const batch = await payload.find({
        collection: FAQ_COLLECTION,
        limit: 100,
        depth: 0,
      });
      if (batch.docs.length === 0) break;
      for (const doc of batch.docs) {
        await payload.delete({ collection: FAQ_COLLECTION, id: doc.id });
      }
    }
  }

  let written = 0;
  for (const group of faqSeedGroups) {
    const items = await Promise.all(
      group.items.map(async (item) => ({
        question: item.question,
        ...(item.label ? { label: item.label } : {}),
        answer: await htmlToLexical(item.answerHtml),
      })),
    );
    await payload.create({
      collection: FAQ_COLLECTION,
      data: {
        _status: "published",
        label: group.label,
        page: group.page,
        items,
      },
    });
    written += items.length;
  }

  log(
    `✅ 常见问题已写入 ${faqSeedPageCount()} 页、${written} 条（默认共 ${faqSeedCount()} 条）`,
  );
}

const payload = await getPayload({ config });

log(force ? "🌱 开始 seed（--force 覆盖已有数据）…" : "🌱 开始 seed（跳过已有数据）…");

await seedAboutPage(payload);
await seedPageSeo(payload);
await seedFaqs(payload);

log("🎉 Seed 完成");

process.exit(0);
