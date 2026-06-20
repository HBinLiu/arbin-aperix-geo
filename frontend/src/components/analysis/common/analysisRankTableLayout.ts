/** 排名表列宽占比：序号 | 品牌 | 指标 | 趋势（合计 100%） */
export const RANK_TABLE_MIN_WIDTH = 320;

export const RANK_TABLE_COL_INDEX = "8%";
export const RANK_TABLE_COL_BRAND = "44%";
export const RANK_TABLE_COL_VALUE = "24%";
export const RANK_TABLE_COL_DELTA = "24%";

/** 无趋势列：序号 | 品牌 | 指标 */
export const RANK_TABLE_COL_INDEX_NO_DELTA = "10%";
export const RANK_TABLE_COL_BRAND_NO_DELTA = "55%";
export const RANK_TABLE_COL_VALUE_NO_DELTA = "35%";

export type RankTableColWidths = {
  index: string;
  brand: string;
  value: string;
  delta?: string;
};

export function rankTableColWidths(showDelta = true): RankTableColWidths {
  if (showDelta) {
    return {
      index: RANK_TABLE_COL_INDEX,
      brand: RANK_TABLE_COL_BRAND,
      value: RANK_TABLE_COL_VALUE,
      delta: RANK_TABLE_COL_DELTA,
    };
  }
  return {
    index: RANK_TABLE_COL_INDEX_NO_DELTA,
    brand: RANK_TABLE_COL_BRAND_NO_DELTA,
    value: RANK_TABLE_COL_VALUE_NO_DELTA,
  };
}
