export function formatScoreDelta(
  current: number | null | undefined,
  previous: number | null | undefined,
): string | null {
  if (current == null || previous == null) return null;
  const delta = current - previous;
  if (Math.abs(delta) < 0.005) return "0.00";
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(2)}`;
}

export function formatDelta(
  current: number | null | undefined,
  previous: number | null | undefined,
): string | null {
  if (current == null || previous == null) return null;
  const delta = (current - previous) * 100;
  if (Math.abs(delta) < 0.05) return "0%";
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(1)}%`;
}

export function isNeutralDelta(delta: string | null | undefined): boolean {
  return delta === "0%" || delta === "0.00";
}

export function formatRate(value: number | null | undefined, suffix = "%"): string {
  if (value == null) return "-";
  const pct = Math.round(value * 1000) / 10;
  if (pct === 0) return `0${suffix}`;
  return `${pct.toFixed(1)}${suffix}`;
}

export function formatScore(value: number | null | undefined): string {
  if (value == null) return "-";
  return value.toFixed(2);
}

/** 计数类指标（引用次数等） */
export function formatCount(value: number | null | undefined): string {
  if (value == null) return "-";
  return String(Math.round(value));
}

export function formatRank(value: number | null | undefined): string {
  if (value == null) return "-";
  return `#${value.toFixed(1)}`;
}

/** 平均排名 KPI（不带 # 前缀） */
export function formatRankMetric(value: number | null | undefined): string {
  if (value == null) return "-";
  return value.toFixed(1);
}

/** 情感得分（0–100 分制） */
export function formatSentimentScore(value: number | null | undefined): string {
  if (value == null) return "-";
  const points = value <= 1 ? value * 100 : value;
  return points.toFixed(1);
}

/** ABSA 原始分（-1~1）转为 0–100 分制，与后端 absa_score_to_points 一致 */
export function absaScoreToPoints(score: number | null | undefined): number | null {
  if (score == null) return null;
  const value = ((Number(score) + 1) / 2) * 100;
  return Math.round(Math.max(0, Math.min(100, value)) * 10) / 10;
}

export function formatSentimentDelta(
  current: number | null | undefined,
  previous: number | null | undefined,
): string | null {
  if (current == null || previous == null) return null;
  const cur = current <= 1 ? current * 100 : current;
  const prev = previous <= 1 ? previous * 100 : previous;
  const delta = cur - prev;
  if (Math.abs(delta) < 0.05) return "0.0";
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(1)}`;
}
