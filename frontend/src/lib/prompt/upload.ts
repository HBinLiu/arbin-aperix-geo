export type PromptCsvRow = {
  topic: string;
  prompt: string;
};

export type PromptCsvParseResult = {
  rows: PromptCsvRow[];
  errors: string[];
};

const REQUIRED_HEADERS = ["topic", "prompt"] as const;

export function buildPromptCsvTemplate(): string {
  return ["topic,prompt", 'Brand visibility,What is the best CRM for startups?'].join("\n");
}

export function downloadPromptCsvTemplate() {
  const blob = new Blob([buildPromptCsvTemplate()], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "prompt-upload-template.csv";
  anchor.click();
  URL.revokeObjectURL(url);
}

export function parsePromptCsv(content: string): PromptCsvParseResult {
  const table = parseCsvTable(content);
  if (table.length === 0) {
    return { rows: [], errors: ["CSV 文件为空。"] };
  }

  const header = table[0].map((cell) => cell.trim().toLowerCase());
  const headerIndex = new Map<string, number>();
  for (const [index, name] of header.entries()) {
    if (name) headerIndex.set(name, index);
  }

  const missing = REQUIRED_HEADERS.filter((key) => !headerIndex.has(key));
  if (missing.length > 0) {
    return { rows: [], errors: [`缺少必填列：${missing.join("、")}。`] };
  }

  const rows: PromptCsvRow[] = [];
  const errors: string[] = [];

  for (let line = 1; line < table.length; line += 1) {
    const cells = table[line];
    const topic = (cells[headerIndex.get("topic")!] ?? "").trim();
    const prompt = (cells[headerIndex.get("prompt")!] ?? "").trim();

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
