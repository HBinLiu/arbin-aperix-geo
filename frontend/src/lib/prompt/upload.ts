import {
  resolveTaxonomyOptionValue,
  taxonomyOptionLabel,
} from "@/lib/prompt/taxonomy";
import type { PromptTaxonomy } from "@/types";

export type PromptCsvRow = {
  topic: string;
  prompt: string;
  searchIntent: string;
  funnelStage: string;
  decisionType: string;
};

export type PromptCsvParseResult = {
  rows: PromptCsvRow[];
  /** 因字段缺失或 taxonomy 无效被跳过的行数 */
  skippedCount: number;
  errors: string[];
};

const COLUMN_ALIASES = {
  topic: ["主题", "topic"],
  prompt: ["提示词", "prompt"],
  searchIntent: ["搜索意图", "search_intent", "intent"],
  funnelStage: ["营销漏斗", "funnel_stage", "funnel"],
  decisionType: ["决策场景", "decision_type", "decision"],
} as const;

const REQUIRED_HEADER_LABELS = [
  "主题",
  "提示词",
  "搜索意图",
  "营销漏斗",
  "决策场景",
] as const;

const REQUIRED_FIELD_LABELS: Record<keyof typeof COLUMN_ALIASES, string> = {
  topic: REQUIRED_HEADER_LABELS[0],
  prompt: REQUIRED_HEADER_LABELS[1],
  searchIntent: REQUIRED_HEADER_LABELS[2],
  funnelStage: REQUIRED_HEADER_LABELS[3],
  decisionType: REQUIRED_HEADER_LABELS[4],
};

export function buildPromptCsvTemplate(taxonomy: PromptTaxonomy): string {
  const searchIntent = taxonomyOptionLabel(
    taxonomy.search_intents,
    taxonomy.default_search_intent,
  );
  const funnelStage = taxonomyOptionLabel(taxonomy.funnel_stages, taxonomy.default_funnel_stage);
  const decisionType = taxonomyOptionLabel(
    taxonomy.decision_types,
    taxonomy.default_decision_type,
  );

  return [
    REQUIRED_HEADER_LABELS.join(","),
    `品牌可见度,初创公司适合用什么CRM？,${searchIntent},${funnelStage},${decisionType}`,
  ].join("\n");
}

export function downloadPromptCsvTemplate(taxonomy: PromptTaxonomy) {
  const blob = new Blob([buildPromptCsvTemplate(taxonomy)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "提示词模版.csv";
  anchor.click();
  URL.revokeObjectURL(url);
}

export function parsePromptCsv(content: string, taxonomy: PromptTaxonomy): PromptCsvParseResult {
  const table = parseCsvTable(content);
  if (table.length === 0) {
    return { rows: [], skippedCount: 0, errors: ["CSV 文件为空。"] };
  }

  const header = table[0].map((cell) => cell.trim().toLowerCase());
  const columnIndexes = {
    topic: findColumnIndex(header, "topic"),
    prompt: findColumnIndex(header, "prompt"),
    searchIntent: findColumnIndex(header, "searchIntent"),
    funnelStage: findColumnIndex(header, "funnelStage"),
    decisionType: findColumnIndex(header, "decisionType"),
  };

  const missing: string[] = [];
  for (const field of Object.keys(columnIndexes) as (keyof typeof columnIndexes)[]) {
    if (columnIndexes[field] == null) {
      missing.push(REQUIRED_FIELD_LABELS[field]);
    }
  }

  if (missing.length > 0) {
    return { rows: [], skippedCount: 0, errors: [`缺少必填列：${missing.join("、")}。`] };
  }

  const rows: PromptCsvRow[] = [];
  let skippedCount = 0;

  for (let line = 1; line < table.length; line += 1) {
    const cells = table[line];
    const topic = (cells[columnIndexes.topic!] ?? "").trim();
    const prompt = (cells[columnIndexes.prompt!] ?? "").trim();
    const searchIntentRaw = (cells[columnIndexes.searchIntent!] ?? "").trim();
    const funnelStageRaw = (cells[columnIndexes.funnelStage!] ?? "").trim();
    const decisionTypeRaw = (cells[columnIndexes.decisionType!] ?? "").trim();

    if (!topic && !prompt && !searchIntentRaw && !funnelStageRaw && !decisionTypeRaw) {
      continue;
    }

    if (!topic || !prompt || !searchIntentRaw || !funnelStageRaw || !decisionTypeRaw) {
      skippedCount += 1;
      continue;
    }

    const searchIntent = resolveTaxonomyOptionValue(taxonomy.search_intents, searchIntentRaw);
    if (!searchIntent) {
      skippedCount += 1;
      continue;
    }

    const funnelStage = resolveTaxonomyOptionValue(taxonomy.funnel_stages, funnelStageRaw);
    if (!funnelStage) {
      skippedCount += 1;
      continue;
    }

    const decisionType = resolveTaxonomyOptionValue(taxonomy.decision_types, decisionTypeRaw);
    if (!decisionType) {
      skippedCount += 1;
      continue;
    }

    rows.push({
      topic,
      prompt,
      searchIntent,
      funnelStage,
      decisionType,
    });
  }

  return { rows, skippedCount, errors: [] };
}

function findColumnIndex(
  header: string[],
  field: keyof typeof COLUMN_ALIASES,
): number | undefined {
  for (const [index, raw] of header.entries()) {
    const name = raw.trim().toLowerCase();
    if (COLUMN_ALIASES[field].some((alias) => name === alias.toLowerCase())) {
      return index;
    }
  }
  return undefined;
}

function parseCsvTable(content: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;

  for (let index = 0; index < content.length; index += 1) {
    const char = content[index];
    const next = content[index + 1];

    if (inQuotes) {
      if (char === '"' && next === '"') {
        field += '"';
        index += 1;
      } else if (char === '"') {
        inQuotes = false;
      } else {
        field += char;
      }
      continue;
    }

    if (char === '"') {
      inQuotes = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\r") {
      continue;
    } else if (char === "\n") {
      row.push(field);
      if (row.some((cell) => cell.trim())) rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }

  if (field || row.length > 0) {
    row.push(field);
    if (row.some((cell) => cell.trim())) rows.push(row);
  }

  return rows;
}
