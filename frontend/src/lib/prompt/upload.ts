export type PromptCsvRow = {
  topic: string;
  prompt: string;
};

export type PromptCsvParseResult = {
  rows: PromptCsvRow[];
  errors: string[];
};

const COLUMN_ALIASES = {
  topic: ["主题", "topic"],
  prompt: ["提示词", "prompt"],
} as const;

const REQUIRED_HEADER_LABELS = ["主题", "提示词"] as const;

export function buildPromptCsvTemplate(): string {
  return ["主题,提示词", "品牌可见度,初创公司适合用什么CRM？"].join("\n");
}

export function downloadPromptCsvTemplate() {
  const blob = new Blob([buildPromptCsvTemplate()], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "提示词模版.csv";
  anchor.click();
  URL.revokeObjectURL(url);
}

export function parsePromptCsv(content: string): PromptCsvParseResult {
  const table = parseCsvTable(content);
  if (table.length === 0) {
    return { rows: [], errors: ["CSV 文件为空。"] };
  }

  const header = table[0].map((cell) => cell.trim().toLowerCase());
  const topicIndex = findColumnIndex(header, "topic");
  const promptIndex = findColumnIndex(header, "prompt");

  const missing: string[] = [];
  if (topicIndex == null) missing.push(REQUIRED_HEADER_LABELS[0]);
  if (promptIndex == null) missing.push(REQUIRED_HEADER_LABELS[1]);

  if (missing.length > 0) {
    return { rows: [], errors: [`缺少必填列：${missing.join("、")}。`] };
  }

  const rows: PromptCsvRow[] = [];
  const errors: string[] = [];

  for (let line = 1; line < table.length; line += 1) {
    const cells = table[line];
    const topic = (cells[topicIndex!] ?? "").trim();
    const prompt = (cells[promptIndex!] ?? "").trim();

    if (!topic && !prompt) continue;

    const rowNo = line + 1;
    if (!topic || !prompt) {
      errors.push(`第 ${rowNo} 行缺少必填字段。`);
      continue;
    }

    rows.push({ topic, prompt });
  }

  if (rows.length === 0 && errors.length === 0) {
    errors.push("CSV 中没有可导入的数据行。");
  }

  return { rows, errors };
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
