import { getPayload } from "payload";
import config from "@payload-config";

import { defaultAboutPage, defaultHomeFaqs } from "./seed/defaults";

const ABOUT_GLOBAL_SLUG = "about-page";
const force = process.argv.includes("--force");

function log(message: string) {
  process.stderr.write(`${message}\n`);
}

function hasAboutContent(data: {
  story?: { paragraphs?: unknown[] | null } | null;
  seo?: { title?: string | null; description?: string | null } | null;
}) {
  const paragraphs = data.story?.paragraphs?.length ?? 0;
  const seo = Boolean(data.seo?.title?.trim() || data.seo?.description?.trim());
  return paragraphs > 0 || seo;
}

async function seedAboutPage(payload: Awaited<ReturnType<typeof getPayload>>) {
  const existing = await payload.findGlobal({
    slug: ABOUT_GLOBAL_SLUG,
    depth: 0,
  });

  if (hasAboutContent(existing) && !force) {
    log("⏭  关于页 Global 已有内容，跳过。使用 --force 覆盖。");
    return;
  }

  await payload.updateGlobal({
    slug: ABOUT_GLOBAL_SLUG,
    data: defaultAboutPage,
  });
  log("✅ 关于页 Global 已写入（_status=published）");
}

async function seedHomeFaqs(payload: Awaited<ReturnType<typeof getPayload>>) {
  const existing = await payload.find({
    collection: "faqs",
    where: { page: { equals: "home" } },
    limit: 1,
    depth: 0,
  });

  if (existing.totalDocs > 0 && !force) {
    log(`⏭  首页 FAQ 已有 ${existing.totalDocs} 条，跳过。使用 --force 覆盖。`);
    return;
  }

  if (force && existing.totalDocs > 0) {
    while (true) {
      const batch = await payload.find({
        collection: "faqs",
        where: { page: { equals: "home" } },
        limit: 100,
        depth: 0,
      });
      if (batch.docs.length === 0) break;
      for (const doc of batch.docs) {
        await payload.delete({ collection: "faqs", id: doc.id });
      }
    }
  }

  for (const faq of defaultHomeFaqs) {
    await payload.create({
      collection: "faqs",
      data: {
        page: "home",
        question: faq.question,
        answer: faq.answer,
        sortOrder: faq.sortOrder,
      },
    });
  }

  log(`✅ 首页 FAQ 已写入 ${defaultHomeFaqs.length} 条`);
}

const payload = await getPayload({ config });

log(force ? "🌱 开始 seed（--force 覆盖已有数据）…" : "🌱 开始 seed（跳过已有数据）…");

await seedAboutPage(payload);
await seedHomeFaqs(payload);

log("🎉 Seed 完成");

process.exit(0);
