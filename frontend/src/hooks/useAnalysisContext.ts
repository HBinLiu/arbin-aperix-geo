import { useMemo } from "react";
import { useOutletContext } from "react-router-dom";

import { dateRangeDays, previousDateRange } from "@/lib/analysis";
import type { AnalysisOutletContext } from "@/types";

export function useAnalysisOutletContext(): AnalysisOutletContext {
  return useOutletContext<AnalysisOutletContext>();
}

/** 分析子页默认使用近 30 天窗口。 */
export function useAnalysisDateRange(days = 30) {
  const { from, to } = useMemo(() => dateRangeDays(days), [days]);
  const prevRange = useMemo(() => previousDateRange(from, to), [from, to]);
  return { from, to, prevRange };
}
