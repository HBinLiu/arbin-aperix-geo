import type { CSSProperties } from "react";

/**
 * 提示词表现页 · 两张表格的布局约定
 *
 * 主题表 / 提示词详情回复表：table 始终 100% 宽，列宽按百分比随容器伸缩；内容不换行；过窄时横向滚动。
 * 提示词表：table 始终 100% 宽；提示词列 flex 吸收剩余宽度，其余列锁定 minWidth；过窄时横向滚动。
 */

/** 主题表列宽（百分比，合计 100%） */
export const TOPIC_TABLE_COLUMNS = [
  { id: "topic", width: "30%" },
  { id: "visibility", width: "18%" },
  { id: "sentiment", width: "20%" },
  { id: "rank", width: "16%" },
  { id: "citation", width: "16%" },
] as const;

/** 主题表最小宽度：容器更窄时出现横向滚动条 */
export const TOPIC_TABLE_MIN_WIDTH = 640;

/** 最小宽度列（px） */
export type PromptTableColumn = {
  id: string;
  minWidth: number;
  /** 占据 table 剩余宽度（提示词列专用，仅一列可为 true） */
  flex?: boolean;
};

/** 提示词表列配置 */
export const PROMPT_TABLE_COLUMNS: readonly PromptTableColumn[] = [
  { id: "prompt", minWidth: 300, flex: true },
  { id: "topic", minWidth: 180 },
  { id: "funnel", minWidth: 120 },
  { id: "visibility", minWidth: 150 },
  { id: "sentiment", minWidth: 150 },
  { id: "rank", minWidth: 150 },
  { id: "citation", minWidth: 150 },
  { id: "intent", minWidth: 100 },
];

/**
 * colgroup：非 flex 列锁定为 minWidth；flex 列不设 width，吸收剩余空间。
 * 若只在 th/td 写 minWidth，table-fixed 会均分列宽，导致提示词列过窄。
 */
export function promptTableColumnColStyle(column: PromptTableColumn): CSSProperties | undefined {
  if (column.flex) {
    return undefined;
  }
  return { width: column.minWidth };
}

/** th / td 样式 */
export function promptTableColumnCellStyle(column: PromptTableColumn): CSSProperties {
  if (column.flex) {
    // maxWidth: 0 配合 truncate，让 flex 列在 table-fixed 中可收缩
    return { minWidth: column.minWidth, maxWidth: 0 };
  }
  return { minWidth: column.minWidth, width: column.minWidth, maxWidth: column.minWidth };
}

/** 提示词表 scroll 区域最小宽度（各列 minWidth 之和） */
export const PROMPT_TABLE_MIN_WIDTH = PROMPT_TABLE_COLUMNS.reduce(
  (sum, column) => sum + column.minWidth,
  0,
);

export const PROMPT_TABLE_COLUMN_COUNT = PROMPT_TABLE_COLUMNS.length;

/** 提示词详情 · 回复列表表列宽（百分比 + 最小宽度，合计百分比可小于 100% 以留给固定列） */
export type PromptDetailResponseTableColumn = {
  id: string;
  width?: string;
  minWidth: number;
};

export const PROMPT_DETAIL_RESPONSE_TABLE_COLUMNS: readonly PromptDetailResponseTableColumn[] = [
  { id: "platform", width: "10%", minWidth: 135 },
  { id: "reply", width: "36%", minWidth: 280 },
  { id: "mentionedBrands", width: "15%", minWidth: 150 },
  { id: "mentioned", width: "12%", minWidth: 135 },
  { id: "rank", width: "12%", minWidth: 135 },
  /** 2026-06-09 04:03:42 */
  { id: "date", minWidth: 180 },
];

export function promptDetailResponseColumnColStyle(
  column: PromptDetailResponseTableColumn,
): CSSProperties {
  if (column.width) {
    return { width: column.width, minWidth: column.minWidth };
  }
  return { width: column.minWidth, minWidth: column.minWidth, maxWidth: column.minWidth };
}

export function promptDetailResponseColumnCellStyle(
  column: PromptDetailResponseTableColumn,
): CSSProperties {
  return { minWidth: column.minWidth };
}

/** 回复列表最小宽度：容器更窄时出现横向滚动条 */
export const PROMPT_DETAIL_RESPONSE_TABLE_MIN_WIDTH = PROMPT_DETAIL_RESPONSE_TABLE_COLUMNS.reduce(
  (sum, column) => sum + column.minWidth,
  0,
);

/** 情感倾向 · 回复列表列宽（百分比 + 最小宽度，合计 100%） */
export type SentimentResponseTableColumn = {
  id: string;
  width: string;
  minWidth: number;
};

export const SENTIMENT_RESPONSE_TABLE_COLUMNS: readonly SentimentResponseTableColumn[] = [
  { id: "platform", width: "12%", minWidth: 120 },
  { id: "prompt", width: "25%", minWidth: 180 },
  { id: "sentiment", width: "12%", minWidth: 120 },
  { id: "reply", width: "35%", minWidth: 240 },
  { id: "date", width: "16%", minWidth: 200 },
];

export const SENTIMENT_RESPONSE_TABLE_MIN_WIDTH = SENTIMENT_RESPONSE_TABLE_COLUMNS.reduce(
  (sum, column) => sum + column.minWidth,
  0,
);

export function sentimentResponseColumnColStyle(
  column: SentimentResponseTableColumn,
): CSSProperties {
  return { width: column.width, minWidth: column.minWidth };
}

export function sentimentResponseColumnCellStyle(
  column: SentimentResponseTableColumn,
): CSSProperties {
  return { minWidth: column.minWidth };
}

export function sentimentResponseColumn(id: string): SentimentResponseTableColumn {
  const column = SENTIMENT_RESPONSE_TABLE_COLUMNS.find((item) => item.id === id);
  if (!column) {
    throw new Error(`Unknown sentiment response table column: ${id}`);
  }
  return column;
}

export const performanceTableClasses = {
  head: "text-muted-foreground bg-muted/80 text-left text-sm [&_th]:whitespace-nowrap [&_th]:px-4 [&_th]:py-3 [&_th]:font-medium",
  row: "border-border h-11 border-t [&>td]:align-middle [&>td]:whitespace-nowrap [&>td]:px-4 [&>td]:py-1",
  topicTable: "w-full table-fixed text-sm",
  promptTable: "w-full table-fixed text-sm",
} as const;

/** 按 id 取列配置 */
export function promptTableColumn(id: string): PromptTableColumn {
  const column = PROMPT_TABLE_COLUMNS.find((item) => item.id === id);
  if (!column) {
    throw new Error(`Unknown prompt table column: ${id}`);
  }
  return column;
}
