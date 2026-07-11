/**
 * 修复 schema 迁移后 Drizzle push 失败或交互确认。
 * - pages Collection → Global 残留
 * - about-page story.paragraphs → story.content 富文本迁移残留
 * - faqs 扁平原子结构 → 每页一条 + items[] 无法自动迁移
 *
 * 用法：npm run repair:schema && npm run seed:force
 */
import pg from "pg";

function log(message: string) {
  process.stderr.write(`${message}\n`);
}

const LEGACY_TABLES = [
  "_about_page_v_version_story_paragraphs",
  "about_page_story_paragraphs",
  "_pages_v_version_story_paragraphs",
  "_pages_v",
  "pages_story_paragraphs",
  "pages",
  "site_settings",
];

const LEGACY_ENUMS = ["enum_pages_status"];

async function repairFaqsSchema(client: pg.Client) {
  const columns = await client.query<{ column_name: string }>(`
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'faqs'
  `);

  if (columns.rows.length === 0) return;

  const names = new Set(columns.rows.map((row) => row.column_name));
  const isFlatSchema = names.has("question") || names.has("sortOrder");

  if (isFlatSchema) {
    log("  ⚠  检测到旧版扁平原子 FAQ 表，删除 faqs 相关表…");
    await client.query('DROP TABLE IF EXISTS "faqs" CASCADE');
    log("  ✓ 已删除旧 faqs 表（Payload push 将重建为「每页一条 + items[]」）");
    return;
  }

  const answerColumn = await client.query<{ data_type: string; udt_name: string }>(`
    SELECT data_type, udt_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'faqs'
      AND column_name = 'answer'
  `);

  if (answerColumn.rows.length === 0) return;

  const { data_type: dataType, udt_name: udtName } = answerColumn.rows[0];
  if (dataType === "json" || dataType === "jsonb" || udtName === "jsonb") {
    log("  ⏭  faqs.answer 已是 jsonb，跳过");
    return;
  }

  log("  ⚠  faqs.answer 为 text（旧 textarea/HTML），清空并改回 jsonb…");
  const deleted = await client.query("DELETE FROM faqs RETURNING 1");
  log(`  ✓ 已删除 ${deleted.rowCount ?? 0} 条 FAQ（HTML 无法转为 Lexical；官网会用代码默认兜底）`);

  await client.query(`
    ALTER TABLE "faqs"
    ALTER COLUMN "answer" TYPE jsonb
    USING NULL::jsonb
  `);
  log("  ✓ faqs.answer 已改为 jsonb");
}

async function repair() {
  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) {
    throw new Error("缺少 DATABASE_URL");
  }

  const client = new pg.Client({ connectionString });
  await client.connect();
  log("🔧 开始修复 CMS schema（清理旧 pages Collection 残留）…");

  const fks = await client.query<{ table_name: string; constraint_name: string }>(`
    SELECT tc.table_name, tc.constraint_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    WHERE kcu.column_name IN ('pages_id', 'site_settings_id')
      AND tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_schema = 'public'
  `);

  for (const row of fks.rows) {
    await client.query(
      `ALTER TABLE "${row.table_name}" DROP CONSTRAINT IF EXISTS "${row.constraint_name}"`,
    );
    log(`  ✓ 删除外键 ${row.constraint_name}（${row.table_name}）`);
  }

  const cols = await client.query<{ table_name: string; column_name: string }>(`
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema = 'public' AND column_name IN ('pages_id', 'site_settings_id')
  `);

  for (const row of cols.rows) {
    await client.query(`ALTER TABLE "${row.table_name}" DROP COLUMN IF EXISTS ${row.column_name}`);
    log(`  ✓ 删除列 ${row.column_name}（${row.table_name}）`);
  }

  for (const table of LEGACY_TABLES) {
    await client.query(`DROP TABLE IF EXISTS "${table}" CASCADE`);
    log(`  ✓ 删除表 ${table}（若存在）`);
  }

  for (const enumName of LEGACY_ENUMS) {
    await client.query(`DROP TYPE IF EXISTS "${enumName}" CASCADE`);
    log(`  ✓ 删除枚举 ${enumName}（若存在）`);
  }

  await repairFaqsSchema(client);

  await client.end();
  log("✅ Schema 修复完成，请重新运行 npm run seed:force");
  process.exit(0);
}

repair().catch((error) => {
  console.error("❌ Schema 修复失败:", error);
  process.exit(1);
});
