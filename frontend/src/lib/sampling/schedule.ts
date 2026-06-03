export const SAMPLING_INTERVAL_OPTIONS = [
  { value: 0, label: "关闭定时采样" },
  { value: 6, label: "每 6 小时" },
  { value: 12, label: "每 12 小时" },
  { value: 24, label: "每天" },
  { value: 72, label: "每 3 天" },
  { value: 168, label: "每周" },
] as const;

export function samplingIntervalLabel(hours: number | undefined): string {
  const option = SAMPLING_INTERVAL_OPTIONS.find((o) => o.value === hours);
  return option?.label ?? "每天";
}

export function formatNextSamplingHint(
  intervalHours: number,
  lastScheduledAt: string | null | undefined,
): string | null {
  if (intervalHours <= 0) return "定时采样已关闭";
  if (!lastScheduledAt) return "将在下个调度周期检查并执行采样";
  const nextMs = new Date(lastScheduledAt).getTime() + intervalHours * 3600 * 1000;
  const next = new Date(nextMs);
  if (Number.isNaN(next.getTime())) return null;
  if (nextMs <= Date.now()) return "已到采样周期，等待调度执行";
  return `预计下次采样：${next.toLocaleString("zh-CN", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" })}`;
}
