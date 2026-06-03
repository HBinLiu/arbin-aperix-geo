/** 近 30 天窗口（按自然日对齐，便于作为稳定 queryKey）。 */
export function defaultDateRange(): { from: string; to: string } {
  return dateRangeDays(30);
}

/** 近 N 天窗口（含当天）。 */
export function dateRangeDays(days: number): { from: string; to: string } {
  const to = new Date();
  to.setHours(23, 59, 59, 999);
  const from = new Date();
  from.setDate(from.getDate() - days + 1);
  from.setHours(0, 0, 0, 0);
  return { from: from.toISOString(), to: to.toISOString() };
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
