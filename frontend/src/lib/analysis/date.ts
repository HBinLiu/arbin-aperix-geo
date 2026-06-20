/** 近 30 天窗口（按自然日对齐，便于作为稳定 queryKey）。 */
export function defaultDateRange(): { from: string; to: string } {
  return dateRangeDays(30);
}

/** 近 N 天窗口（含当天）。 */
export function dateRangeDays(days: number): { from: string; to: string } {
  const to = endOfDay(new Date());
  const from = startOfDay(new Date());
  from.setDate(from.getDate() - days + 1);
  return { from: from.toISOString(), to: to.toISOString() };
}

function startOfDay(date: Date): Date {
  const next = new Date(date);
  next.setHours(0, 0, 0, 0);
  return next;
}

function endOfDay(date: Date): Date {
  const next = new Date(date);
  next.setHours(23, 59, 59, 999);
  return next;
}

/** ISO 字符串转本地日历日期（忽略时分秒）。 */
export function isoToLocalDate(iso: string): Date {
  const date = new Date(iso);
  return startOfDay(date);
}

/** 本地日期区间转 ISO（from 当天 00:00，to 当天 23:59:59.999）。 */
export function localDatesToIso(from: Date, to: Date): { from: string; to: string } {
  return { from: startOfDay(from).toISOString(), to: endOfDay(to).toISOString() };
}

/** 与当前窗口等长的上一周期。 */
export function previousDateRange(from: string, to: string): { from: string; to: string } {
  const fromDt = new Date(from);
  const toDt = new Date(to);
  const spanMs = toDt.getTime() - fromDt.getTime();
  const prevTo = new Date(fromDt.getTime() - 1);
  prevTo.setHours(23, 59, 59, 999);
  const prevFrom = new Date(prevTo.getTime() - spanMs);
  prevFrom.setHours(0, 0, 0, 0);
  return { from: prevFrom.toISOString(), to: prevTo.toISOString() };
}

export function formatDateRangeLabel(from: string, to: string): string {
  const format = (iso: string) => {
    const d = new Date(iso);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}/${m}/${day}`;
  };
  return `${format(from)} - ${format(to)}`;
}
