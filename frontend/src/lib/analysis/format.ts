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
  if (Math.abs(delta) < 0.05) return "0.0%";
  const sign = delta > 0 ? "+" : "";
  return `${sign}${delta.toFixed(1)}%`;
}

export function formatRate(value: number | null | undefined, suffix = "%"): string {
  if (value == null) return "暂无数据";
  return `${(value * 100).toFixed(1)}${suffix}`;
}

export function formatScore(value: number | null | undefined): string {
  if (value == null) return "暂无数据";
  return value.toFixed(2);
}

export function formatRank(value: number | null | undefined): string {
  if (value == null) return "暂无数据";
  return `#${value.toFixed(1)}`;
}
