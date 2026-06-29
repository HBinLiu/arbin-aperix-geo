export type SamplingFrequencyCode = "daily_1" | "daily_3" | "daily_7";

export type SamplingIntervalOption = {
  value: number;
  label: string;
  frequency: SamplingFrequencyCode;
};

/** UI 选项：value 为小时数（与历史字段对齐）；调度按 frequency 解析为整天间隔。 */
export const SAMPLING_INTERVAL_OPTIONS: SamplingIntervalOption[] = [
  { value: 24, label: "每天", frequency: "daily_1" },
  { value: 72, label: "每3天", frequency: "daily_3" },
  { value: 168, label: "每周", frequency: "daily_7" },
];

const FREQUENCY_TO_HOURS: Record<SamplingFrequencyCode, number> = {
  daily_1: 24,
  daily_3: 72,
  daily_7: 168,
};

const SHANGHAI_TZ = "Asia/Shanghai";

function normalizeFrequencyCode(code: string | null | undefined): SamplingFrequencyCode {
  const normalized = (code ?? "daily_1").trim().toLowerCase();
  if (normalized === "daily_3" || normalized === "daily_7") return normalized;
  return "daily_1";
}

export function samplingFrequencyToHours(code: string | null | undefined): number {
  return FREQUENCY_TO_HOURS[normalizeFrequencyCode(code)];
}

export function samplingIntervalDays(code: string | null | undefined): number {
  const normalized = normalizeFrequencyCode(code);
  if (normalized === "daily_3") return 3;
  if (normalized === "daily_7") return 7;
  return 1;
}

export function hoursToSamplingFrequency(hours: string | number): SamplingFrequencyCode {
  const parsed = typeof hours === "string" ? Number(hours) : hours;
  const match = SAMPLING_INTERVAL_OPTIONS.find((opt) => opt.value === parsed);
  return match?.frequency ?? "daily_1";
}

export function samplingIntervalLabel(hours: number): string {
  const match = SAMPLING_INTERVAL_OPTIONS.find((opt) => opt.value === hours);
  return match?.label ?? "每天";
}

export function allowedSamplingIntervalOptions(planFrequency: string | null | undefined): SamplingIntervalOption[] {
  const planDays = samplingIntervalDays(planFrequency);
  return SAMPLING_INTERVAL_OPTIONS.filter((opt) => samplingIntervalDays(opt.frequency) >= planDays);
}

function shanghaiCalendarDate(date: Date): { year: number; month: number; day: number } {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: SHANGHAI_TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const pick = (type: string) => Number(parts.find((p) => p.type === type)?.value ?? 0);
  return { year: pick("year"), month: pick("month"), day: pick("day") };
}

function addCalendarDays(base: { year: number; month: number; day: number }, days: number): Date {
  const utc = Date.UTC(base.year, base.month - 1, base.day + days);
  return new Date(utc);
}

function formatShanghaiDate(date: Date): string {
  return date.toLocaleDateString("zh-CN", {
    timeZone: SHANGHAI_TZ,
    month: "numeric",
    day: "numeric",
  });
}

function compareCalendarDates(
  a: { year: number; month: number; day: number },
  b: { year: number; month: number; day: number },
): number {
  if (a.year !== b.year) return a.year - b.year;
  if (a.month !== b.month) return a.month - b.month;
  return a.day - b.day;
}

/**
 * 下次采样提示（与后端 schedule 一致：北京时间日历日 + interval_days）。
 * 实际入队还需满足当日采样窗口与品牌 slot，此处仅展示「间隔意义上的最早日期」。
 */
export function nextSamplingHint(
  lastSampledAt: string | null | undefined,
  frequencyCode: string | null | undefined,
): string | null {
  if (!lastSampledAt?.trim()) {
    return "尚未采样，将在下一窗口自动执行";
  }
  const last = new Date(lastSampledAt);
  if (Number.isNaN(last.getTime())) {
    return null;
  }

  const intervalDays = samplingIntervalDays(frequencyCode);
  const lastDay = shanghaiCalendarDate(last);
  const nextDay = addCalendarDays(lastDay, intervalDays);
  const today = shanghaiCalendarDate(new Date());

  if (compareCalendarDates(today, shanghaiCalendarDate(nextDay)) >= 0) {
    return "已达采样间隔，将在今日窗口内执行";
  }
  return `下次预计 ${formatShanghaiDate(nextDay)}`;
}

export { normalizeFrequencyCode as normalizeSamplingFrequencyCode };
