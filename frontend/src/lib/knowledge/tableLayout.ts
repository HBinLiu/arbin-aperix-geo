/** 知识库来源表列宽（百分比，合计 100%） */
export const KNOWLEDGE_SOURCE_TABLE_COLUMNS = [
  { id: "name", width: "30%" },
  { id: "size", width: "14%" },
  { id: "kind", width: "14%" },
  { id: "status", width: "14%" },
  { id: "updatedAt", width: "16%" },
  { id: "actions", width: "12%" },
] as const;

/** 来源表最小宽度：容器更窄时出现横向滚动条 */
export const KNOWLEDGE_SOURCE_TABLE_MIN_WIDTH = 820;

export const KNOWLEDGE_SOURCE_TABLE_COLUMN_COUNT = KNOWLEDGE_SOURCE_TABLE_COLUMNS.length;
